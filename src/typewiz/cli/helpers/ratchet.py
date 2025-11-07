# Copyright (c) 2024 PantherianCodeX
"""Helper utilities for ratchet CLI commands."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final, cast

from typewiz.cli_helpers import (
    parse_comma_separated,
    parse_key_value_entries,
)
from typewiz.model_types import SeverityLevel, SignaturePolicy
from typewiz.ratchet.models import RatchetModel
from typewiz.type_aliases import RunId

DEFAULT_SEVERITIES: Final[tuple[SeverityLevel, SeverityLevel]] = (
    SeverityLevel.ERROR,
    SeverityLevel.WARNING,
)
MANIFEST_CANDIDATE_NAMES: Final[tuple[str, ...]] = (
    "typing_audit.json",
    "typing_audit_manifest.json",
    "reports/typing/typing_audit.json",
    "reports/typing/manifest.json",
)
DEFAULT_RATCHET_FILENAME: Final[Path] = Path(".typewiz/ratchet.json")


def _coerce_severity_value(value: str | SeverityLevel) -> SeverityLevel:
    return value if isinstance(value, SeverityLevel) else SeverityLevel.from_str(value)


def parse_target_entries(entries: Sequence[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    if not entries:
        return mapping
    for key, raw_value in parse_key_value_entries(entries, argument="--target"):
        try:
            budget = max(0, int(raw_value))
        except ValueError as exc:  # pragma: no cover - validated via CLI tests
            raise SystemExit(f"Invalid target value '{raw_value}' for key '{key}'") from exc
        mapping[key] = budget
    return mapping


def split_target_mapping(
    mapping: Mapping[str, int],
) -> tuple[dict[SeverityLevel, int], dict[str, dict[SeverityLevel, int]]]:
    global_targets: dict[SeverityLevel, int] = {}
    per_run: dict[str, dict[SeverityLevel, int]] = {}
    for raw_key, value in mapping.items():
        key = raw_key.strip()
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
            global_targets[severity] = budget
    return global_targets, per_run


def apply_target_overrides(model: RatchetModel, overrides: Mapping[str, int]) -> None:
    if not overrides:
        return
    global_targets, per_run = split_target_mapping(overrides)
    for run_id, run_budget in model.runs.items():
        if global_targets:
            run_budget.targets.update(global_targets)
        if run_id in per_run:
            run_budget.targets.update(per_run[run_id])


def normalise_runs(runs: Sequence[str | RunId] | None) -> list[RunId]:
    if not runs:
        return []
    normalised: list[RunId] = []
    for value in runs:
        token = str(value).strip()
        if not token:
            continue
        normalised.append(RunId(token))
    return normalised


def resolve_runs(
    cli_runs: Sequence[str | RunId] | None, config_runs: Sequence[str | RunId]
) -> list[RunId] | None:
    runs = normalise_runs(cli_runs) or normalise_runs(config_runs)
    return runs or None


def resolve_severities(
    cli_value: str | None, config_values: Sequence[SeverityLevel]
) -> list[SeverityLevel]:
    raw_values: Sequence[str | SeverityLevel]
    if cli_value:
        raw_values = parse_comma_separated(cli_value)
    else:
        raw_values = list(config_values)
    normalised: list[SeverityLevel] = [
        _coerce_severity_value(value) for value in raw_values if value
    ]
    if not normalised:
        config_normalised: list[SeverityLevel] = [
            _coerce_severity_value(value) for value in config_values if value
        ]
        default_severities: list[SeverityLevel] = list(DEFAULT_SEVERITIES)
        normalised = config_normalised or default_severities
    seen: set[SeverityLevel] = set()
    ordered: list[SeverityLevel] = []
    for severity in normalised:
        if severity not in seen:
            seen.add(severity)
            ordered.append(severity)
    return ordered


def resolve_signature_policy(
    cli_value: str | None, config_value: SignaturePolicy
) -> SignaturePolicy:
    if cli_value is None:
        return config_value
    try:
        return SignaturePolicy.from_str(cli_value)
    except ValueError as exc:
        readable = ", ".join(policy.value for policy in SignaturePolicy)
        raise SystemExit(
            f"Unknown signature policy '{cli_value}'. Valid values: {readable}"
        ) from exc


def resolve_limit(cli_limit: int | None, config_limit: int | None) -> int | None:
    return cli_limit if cli_limit is not None else config_limit


def resolve_summary_only(cli_summary: bool, config_summary: bool) -> bool:
    return bool(cli_summary) or config_summary


def resolve_path(project_root: Path, candidate: Path) -> Path:
    return candidate if candidate.is_absolute() else (project_root / candidate).resolve()


def discover_manifest_path(
    project_root: Path,
    *,
    explicit: Path | None,
    configured: Path | None,
) -> Path:
    if explicit is not None:
        resolved = resolve_path(project_root, explicit)
        if not resolved.exists():
            raise SystemExit(f"Manifest not found: {resolved}")
        return resolved
    if configured is not None:
        resolved = resolve_path(project_root, configured)
        if resolved.exists():
            return resolved
    for name in MANIFEST_CANDIDATE_NAMES:
        candidate = (project_root / name).resolve()
        if candidate.exists():
            return candidate
    raise SystemExit(
        "No manifest discovered. Provide --manifest or set 'ratchet.manifest_path' in typewiz.toml."
    )


def discover_ratchet_path(
    project_root: Path,
    *,
    explicit: Path | None,
    configured: Path | None,
    require_exists: bool,
) -> Path:
    if explicit is not None:
        resolved = resolve_path(project_root, explicit)
    elif configured is not None:
        resolved = resolve_path(project_root, configured)
    else:
        resolved = (project_root / DEFAULT_RATCHET_FILENAME).resolve()
    if require_exists and not resolved.exists():
        raise SystemExit(f"Ratchet file not found at {resolved}")
    return resolved


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


__all__ = [
    "DEFAULT_RATCHET_FILENAME",
    "DEFAULT_SEVERITIES",
    "MANIFEST_CANDIDATE_NAMES",
    "apply_target_overrides",
    "discover_manifest_path",
    "discover_ratchet_path",
    "ensure_parent",
    "normalise_runs",
    "parse_target_entries",
    "resolve_limit",
    "resolve_path",
    "resolve_runs",
    "resolve_severities",
    "resolve_signature_policy",
    "resolve_summary_only",
    "split_target_mapping",
]
