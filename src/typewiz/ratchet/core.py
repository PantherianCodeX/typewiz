# Copyright (c) 2024 PantherianCodeX
"""Core ratchet algorithms for building, comparing, and updating budgets."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping, MutableMapping, Sequence
from pathlib import Path
from typing import Final, cast

from ..data_validation import coerce_int, coerce_mapping, coerce_object_list
from ..model_types import Mode, SeverityLevel
from ..type_aliases import RunId, ToolName
from ..typed_manifest import ManifestData, ModeStr
from ..utils import JSONValue
from .models import (
    RATCHET_SCHEMA_VERSION,
    EngineSignaturePayload,
    EngineSignaturePayloadWithHash,
    RatchetModel,
    RatchetPathBudgetModel,
    RatchetRunBudgetModel,
)
from .summary import RatchetFinding, RatchetReport, RatchetRunReport

DEFAULT_SEVERITIES: Final[tuple[SeverityLevel, SeverityLevel]] = (
    SeverityLevel.ERROR,
    SeverityLevel.WARNING,
)
MODE_MAP: Final[dict[str, ModeStr]] = {
    "current": "current",
    "full": "full",
}


def _coerce_mode_str(value: object) -> ModeStr | None:
    if not isinstance(value, str):
        return None
    token = value.strip()
    try:
        mode_value = Mode.from_str(token).value
    except ValueError:
        return None
    return MODE_MAP.get(mode_value)


def _severity_counts_from_file(entry: Mapping[str, JSONValue]) -> Counter[SeverityLevel]:
    counts: Counter[SeverityLevel] = Counter()
    diagnostics = coerce_object_list(entry.get("diagnostics"))
    if diagnostics:
        for diag_obj in diagnostics:
            diag_map = coerce_mapping(diag_obj)
            sev_raw = diag_map.get("severity")
            if isinstance(sev_raw, str) and sev_raw:
                counts[SeverityLevel.from_str(sev_raw)] += 1
        if counts:
            return counts
    errors = coerce_int(entry.get("errors"))
    warnings = coerce_int(entry.get("warnings"))
    information = coerce_int(entry.get("information"))
    if errors:
        counts[SeverityLevel.ERROR] = errors
    if warnings:
        counts[SeverityLevel.WARNING] = warnings
    if information:
        counts[SeverityLevel.INFORMATION] = information
    return counts


def _optional_str(raw: Mapping[str, JSONValue], key: str) -> str | None:
    value = raw.get(key)
    return value if isinstance(value, str) and value else None


def _string_list(raw: Mapping[str, JSONValue], key: str) -> list[str]:
    values = coerce_object_list(raw.get(key))
    return [str(item) for item in values] if values else []


def _normalise_overrides(raw: Mapping[str, JSONValue]) -> list[dict[str, JSONValue]]:
    overrides = coerce_object_list(raw.get("overrides"))
    normalised: list[dict[str, JSONValue]] = []
    for override in overrides:
        override_map = coerce_mapping(override)
        normalised.append({str(key): override_map[key] for key in sorted(override_map)})
    return normalised


def _normalise_category_mapping(raw: Mapping[str, JSONValue]) -> dict[str, list[str]]:
    category_mapping = raw.get("categoryMapping")
    if not isinstance(category_mapping, Mapping):
        return {}
    mapping_out: dict[str, list[str]] = {}
    category_map = coerce_mapping(category_mapping)
    for key in sorted(category_map):
        values = coerce_object_list(category_map[key])
        mapping_out[str(key)] = [str(item) for item in values] if values else []
    return mapping_out


def _canonicalise_engine_options(
    raw: Mapping[str, JSONValue] | None,
) -> MutableMapping[str, JSONValue]:
    if not raw:
        return {}
    result: dict[str, JSONValue] = {}
    if profile := _optional_str(raw, "profile"):
        result["profile"] = profile
    if config_file := _optional_str(raw, "configFile"):
        result["configFile"] = config_file
    for key in ("pluginArgs", "include", "exclude"):
        values = _string_list(raw, key)
        if values:
            json_list: list[JSONValue] = [cast("JSONValue", value) for value in values]
            result[key] = json_list
    overrides = _normalise_overrides(raw)
    if overrides:
        result["overrides"] = cast(JSONValue, overrides)
    category_mapping = _normalise_category_mapping(raw)
    if category_mapping:
        result["categoryMapping"] = cast(JSONValue, category_mapping)
    return result


def _normalise_severity_list(
    severities: Sequence[str | SeverityLevel] | None,
) -> list[SeverityLevel]:
    if not severities:
        return list(DEFAULT_SEVERITIES)
    severity_set: set[SeverityLevel] = {
        item if isinstance(item, SeverityLevel) else SeverityLevel.from_str(item)
        for item in severities
        if item
    }
    if not severity_set:
        severity_set = set(DEFAULT_SEVERITIES)
    return sorted(severity_set, key=lambda severity: severity.value)


def _split_targets(
    targets: Mapping[str, int] | None,
) -> tuple[dict[SeverityLevel, int], dict[str, dict[SeverityLevel, int]]]:
    if not targets:
        return {}, {}
    global_map: dict[SeverityLevel, int] = {}
    per_run: dict[str, dict[SeverityLevel, int]] = {}
    for raw_key, value in targets.items():
        key = str(raw_key).strip()
        if not key:
            continue
        budget = max(0, int(value))
        if "." in key:
            run_id, severity_token = key.rsplit(".", 1)
            severity = SeverityLevel.from_str(severity_token)
            run_key = run_id.strip()
            entry = per_run.setdefault(run_key, cast(dict[SeverityLevel, int], {}))
            entry[severity] = budget
        else:
            severity = SeverityLevel.from_str(key)
            global_map[severity] = budget
    return global_map, per_run


def _build_path_budgets(
    per_file_entries: Sequence[object],
    severities: Sequence[SeverityLevel],
) -> dict[str, RatchetPathBudgetModel]:
    path_budgets: dict[str, RatchetPathBudgetModel] = {}
    for entry in per_file_entries:
        entry_map = coerce_mapping(entry)
        path = entry_map.get("path")
        if not isinstance(path, str) or not path:
            continue
        counts = _severity_counts_from_file(entry_map)
        if not counts:
            counts = Counter({severity: 0 for severity in severities})
        budgets: dict[SeverityLevel, int] = {
            severity: max(0, counts.get(severity, 0)) for severity in severities
        }
        path_budgets[path] = RatchetPathBudgetModel(severities=budgets)
    return path_budgets


def _engine_signature_payload(run: Mapping[str, JSONValue]) -> EngineSignaturePayload:
    engine_options = _canonicalise_engine_options(
        coerce_mapping(run.get("engineOptions"))
        if isinstance(run.get("engineOptions"), Mapping)
        else None,
    )
    engine_options_dict: dict[str, JSONValue] = dict(engine_options)
    mode = _coerce_mode_str(run.get("mode"))
    return EngineSignaturePayload(
        tool=str(run.get("tool")) if run.get("tool") is not None else None,
        mode=mode,
        engineOptions=engine_options_dict,
    )


def _engine_signature_hash(payload: EngineSignaturePayload) -> str:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _signature_payload_with_hash(run: Mapping[str, JSONValue]) -> EngineSignaturePayloadWithHash:
    signature_payload = _engine_signature_payload(run)
    payload_with_hash: EngineSignaturePayloadWithHash = {
        "tool": signature_payload["tool"],
        "mode": signature_payload["mode"],
        "engineOptions": signature_payload["engineOptions"],
        "hash": _engine_signature_hash(signature_payload),
    }
    return payload_with_hash


def _collect_manifest_runs(manifest: ManifestData) -> list[Mapping[str, JSONValue]]:
    runs_raw = manifest.get("runs")
    if not isinstance(runs_raw, Sequence):
        return []
    return [coerce_mapping(run_obj) for run_obj in runs_raw]


def _select_run_ids(manifest: ManifestData, requested: Sequence[str] | None) -> list[RunId]:
    runs = _collect_manifest_runs(manifest)
    all_ids: list[RunId] = []
    for run in runs:
        tool_raw = str(run.get("tool", "")).strip()
        mode = str(run.get("mode", "")).strip()
        if not tool_raw or not mode:
            continue
        tool = ToolName(tool_raw)
        all_ids.append(RunId(f"{tool}:{mode}"))
    if requested:
        requested_norm = {item.strip() for item in requested if item and item.strip()}
        return [run_id for run_id in all_ids if run_id in requested_norm]
    return all_ids


def _run_by_id(manifest: ManifestData) -> dict[RunId, Mapping[str, JSONValue]]:
    lookup: dict[RunId, Mapping[str, JSONValue]] = {}
    for run in _collect_manifest_runs(manifest):
        tool_raw = str(run.get("tool", "")).strip()
        mode = str(run.get("mode", "")).strip()
        if not tool_raw or not mode:
            continue
        tool = ToolName(tool_raw)
        lookup[RunId(f"{tool}:{mode}")] = run
    return lookup


def build_ratchet_from_manifest(
    *,
    manifest: ManifestData,
    runs: Sequence[str] | None = None,
    severities: Sequence[str] | None = None,
    targets: Mapping[str, int] | None = None,
    manifest_path: str | Path | None = None,
) -> RatchetModel:
    """Create a ratchet budget from a manifest payload."""

    selected_runs = _select_run_ids(manifest, runs)
    run_lookup = _run_by_id(manifest)

    severity_list = _normalise_severity_list(severities)
    global_targets, per_run_targets = _split_targets(targets)

    runs_budget: dict[str, RatchetRunBudgetModel] = {}
    for run_id in selected_runs:
        run = run_lookup.get(run_id)
        if not run:
            continue
        run_id_str = str(run_id)
        per_file_entries = coerce_object_list(run.get("perFile"))
        path_budgets = _build_path_budgets(per_file_entries, severity_list)
        run_specific = dict(global_targets)
        run_specific.update(per_run_targets.get(run_id_str, {}))
        runs_budget[run_id_str] = RatchetRunBudgetModel(
            severities=severity_list,
            paths=path_budgets,
            targets=run_specific,
            engine_signature=_signature_payload_with_hash(run),
        )

    generated_at = str(manifest.get("generatedAt")) if manifest.get("generatedAt") else ""
    project_root_str = manifest.get("projectRoot")
    project_root = (
        Path(project_root_str) if isinstance(project_root_str, str) and project_root_str else None
    )
    manifest_path_resolved = None
    if manifest_path:
        manifest_path_resolved = Path(manifest_path)

    return RatchetModel(
        schemaVersion=RATCHET_SCHEMA_VERSION,
        generatedAt=generated_at,
        manifestPath=manifest_path_resolved,
        projectRoot=project_root,
        runs=runs_budget,
    )


def _collect_path_counts(per_file_entries: Sequence[object]) -> dict[str, Counter[SeverityLevel]]:
    counts_by_path: dict[str, Counter[SeverityLevel]] = {}
    for entry in per_file_entries:
        entry_map = coerce_mapping(entry)
        path = entry_map.get("path")
        if not isinstance(path, str) or not path:
            continue
        counts_by_path[path] = _severity_counts_from_file(entry_map)
    return counts_by_path


def _updated_path_budgets(
    run_budget: RatchetRunBudgetModel,
    path_counts: Mapping[str, Counter[SeverityLevel]],
) -> dict[str, RatchetPathBudgetModel]:
    new_paths: dict[str, RatchetPathBudgetModel] = {}
    for path, budget in run_budget.paths.items():
        current_counts = path_counts.get(path, Counter[SeverityLevel]())
        severity_budgets: dict[SeverityLevel, int] = {}
        for severity in run_budget.severities:
            allowed = budget.severities.get(severity, 0)
            actual = current_counts.get(severity, 0)
            target = run_budget.targets.get(severity, 0)
            new_budget = allowed if actual >= allowed else max(target, actual)
            severity_budgets[severity] = new_budget
        new_paths[path] = RatchetPathBudgetModel(severities=severity_budgets)
    return new_paths


def _compare_severity_budget(
    *,
    path: str,
    severity: SeverityLevel,
    allowed: int,
    actual: int,
) -> tuple[RatchetFinding | None, RatchetFinding | None]:
    if actual > allowed:
        return RatchetFinding(
            path=path,
            severity=severity,
            allowed=allowed,
            actual=actual,
        ), None
    if actual < allowed:
        return None, RatchetFinding(
            path=path,
            severity=severity,
            allowed=allowed,
            actual=actual,
        )
    return None, None


def _evaluate_run_report(
    run_id: RunId,
    run_budget: RatchetRunBudgetModel,
    manifest_run: Mapping[str, JSONValue],
) -> RatchetRunReport:
    by_path = _collect_path_counts(coerce_object_list(manifest_run.get("perFile")))
    signature_payload_with_hash = _signature_payload_with_hash(manifest_run)
    expected_signature = run_budget.engine_signature
    signature_matches = expected_signature is not None and expected_signature.get(
        "hash"
    ) == signature_payload_with_hash.get("hash")

    violations: list[RatchetFinding] = []
    improvements: list[RatchetFinding] = []
    for path in sorted(set(run_budget.paths) | set(by_path)):
        path_budget = run_budget.paths.get(path, RatchetPathBudgetModel(severities={}))
        actual_counts = by_path.get(path)
        if actual_counts is None:
            actual_counts = Counter[SeverityLevel]()
        for severity in run_budget.severities:
            allowed = path_budget.severities.get(severity, 0)
            actual = actual_counts.get(severity, 0)
            violation, improvement = _compare_severity_budget(
                path=path,
                severity=severity,
                allowed=allowed,
                actual=actual,
            )
            if violation:
                violations.append(violation)
            elif improvement:
                improvements.append(improvement)

    return RatchetRunReport(
        run_id=run_id,
        severities=list(run_budget.severities),
        violations=violations,
        improvements=improvements,
        signature_matches=signature_matches,
        expected_signature=expected_signature,
        actual_signature=signature_payload_with_hash,
    )


def compare_manifest_to_ratchet(
    *,
    manifest: ManifestData,
    ratchet: RatchetModel,
    runs: Sequence[str] | None = None,
) -> RatchetReport:
    """Compare a manifest payload against a ratchet budget."""

    run_lookup = _run_by_id(manifest)
    if runs is None:
        selected_runs: list[RunId] = [RunId(run_id) for run_id in ratchet.runs.keys()]
    else:
        selected_runs = [RunId(item.strip()) for item in runs if item and item.strip()]
    reports: list[RatchetRunReport] = []
    for run_id in selected_runs:
        run_budget = ratchet.runs.get(str(run_id))
        manifest_run = run_lookup.get(run_id)
        if not run_budget or not manifest_run:
            continue
        reports.append(_evaluate_run_report(run_id, run_budget, manifest_run))
    return RatchetReport(runs=reports)


def apply_auto_update(
    *,
    manifest: ManifestData,
    ratchet: RatchetModel,
    runs: Sequence[str] | None = None,
    generated_at: str,
) -> RatchetModel:
    """Return a new ratchet model with budgets reduced to current manifest counts."""

    report = compare_manifest_to_ratchet(manifest=manifest, ratchet=ratchet, runs=runs)
    updated_runs: dict[str, RatchetRunBudgetModel] = {}
    run_lookup = _run_by_id(manifest)

    for run_report in report.runs:
        run_id_str = str(run_report.run_id)
        run_budget = ratchet.runs.get(run_id_str)
        manifest_run = run_lookup.get(run_report.run_id)
        if not run_budget or not manifest_run:
            continue
        per_file_entries = coerce_object_list(manifest_run.get("perFile"))
        path_counts = _collect_path_counts(per_file_entries)
        new_paths = _updated_path_budgets(run_budget, path_counts)
        actual_signature_payload_with_hash = _signature_payload_with_hash(manifest_run)
        updated_runs[run_id_str] = RatchetRunBudgetModel(
            severities=list(run_budget.severities),
            paths=new_paths,
            targets=dict(run_budget.targets),
            engine_signature=actual_signature_payload_with_hash,
        )

    return RatchetModel(
        schemaVersion=ratchet.schema_version,
        generatedAt=generated_at,
        manifestPath=ratchet.manifest_path,
        projectRoot=ratchet.project_root,
        runs=updated_runs or ratchet.runs,
    )


def refresh_signatures(
    *,
    manifest: ManifestData,
    ratchet: RatchetModel,
    runs: Sequence[str] | None = None,
    generated_at: str,
) -> RatchetModel:
    """Return a ratchet model with refreshed engine signature metadata."""

    run_lookup = _run_by_id(manifest)
    selected_runs = set(runs or ratchet.runs.keys())
    refreshed_runs: dict[str, RatchetRunBudgetModel] = {}
    for run_id, budget in ratchet.runs.items():
        if runs and run_id not in selected_runs:
            refreshed_runs[run_id] = budget
            continue
        manifest_run = run_lookup.get(RunId(run_id))
        if manifest_run is None:
            refreshed_runs[run_id] = budget
            continue
        signature = _signature_payload_with_hash(manifest_run)
        refreshed_runs[run_id] = RatchetRunBudgetModel(
            severities=list(budget.severities),
            paths=dict(budget.paths),
            targets=dict(budget.targets),
            engine_signature=signature,
        )
    return RatchetModel(
        schemaVersion=ratchet.schema_version,
        generatedAt=generated_at,
        manifestPath=ratchet.manifest_path,
        projectRoot=ratchet.project_root,
        runs=refreshed_runs,
    )
