# Copyright 2025 CrownOps Engineering
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Dashboard summary builder for ratchetr.

This module handles the construction of dashboard summaries from manifest data.
It processes type checking runs, aggregates diagnostics, computes readiness metrics,
and structures the data for rendering in HTML or Markdown formats.
"""

from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from ratchetr.config.validation import (
    coerce_int,
    coerce_mapping,
    coerce_object_list,
    coerce_str_list,
)
from ratchetr.core.categories import coerce_category_key
from ratchetr.core.model_types import (
    CategoryMapping,
    LogComponent,
    OverrideEntry,
    ReadinessStatus,
    SeverityLevel,
    SummaryTabName,
    clone_override_entries,
)
from ratchetr.core.summary_types import (
    TAB_KEY_ENGINES,
    TAB_KEY_HOTSPOTS,
    TAB_KEY_OVERVIEW,
    TAB_KEY_READINESS,
    TAB_KEY_RUNS,
    CountsByCategory,
    CountsByRule,
    CountsBySeverity,
    ReadinessOptionEntry,
    ReadinessOptionsPayload,
    ReadinessTab,
    RulePathEntry,
    SummaryData,
    SummaryFileEntry,
    SummaryFolderEntry,
    SummaryRunEntry,
    SummaryTabs,
)
from ratchetr.core.type_aliases import CategoryKey, RelPath, RunId
from ratchetr.exceptions import RatchetrTypeError
from ratchetr.logging import structured_extra
from ratchetr.manifest.loader import load_manifest_data
from ratchetr.readiness.compute import (
    DEFAULT_CLOSE_THRESHOLD,
    ReadinessEntry,
    ReadinessOptions,
    ReadinessPayload,
    compute_readiness,
)

if TYPE_CHECKING:
    from pathlib import Path

    from ratchetr.json import JSONValue
    from ratchetr.manifest.typed import EngineOptionsEntry, ManifestData, ToolSummary

logger: logging.Logger = logging.getLogger("ratchetr.dashboard")


@dataclass(slots=True)
class _FolderAccumulators:
    """Accumulates folder-level diagnostic statistics across multiple runs.

    Attributes:
        totals: Mapping of folder paths to severity level counters.
        counts: Number of runs that included diagnostics for each folder.
        code_totals: Mapping of folder paths to diagnostic code counters.
        category_totals: Mapping of folder paths to category counters.
        recommendations: Set of recommendations for each folder path.
    """

    totals: dict[str, Counter[str]]
    counts: dict[str, int]
    code_totals: dict[str, Counter[str]]
    category_totals: dict[str, Counter[CategoryKey]]
    recommendations: dict[str, set[str]]

    def build_entries(self) -> list[ReadinessEntry]:
        """Build readiness entries from accumulated folder statistics.

        Returns:
            List of readiness entries containing aggregated diagnostic counts,
            code counts, category counts, and recommendations for each folder.
        """
        entries: list[ReadinessEntry] = []
        for path, counts in self.totals.items():
            entries.append(
                {
                    "path": path,
                    "errors": counts["errors"],
                    "warnings": counts["warnings"],
                    "information": counts["information"],
                    "codeCounts": dict(self.code_totals.get(path, {})),
                    "categoryCounts": dict(self.category_totals.get(path, {})),
                    "recommendations": sorted(self.recommendations.get(path, [])),
                },
            )
        return entries


@dataclass(slots=True)
class _SummaryState:
    """Maintains aggregated state while building dashboard summaries.

    Attributes:
        run_summary: Summary data for each type checking run.
        severity_totals: Total diagnostic counts by severity level.
        rule_totals: Total diagnostic counts by rule code.
        category_totals: Total diagnostic counts by category.
        folder_stats: Accumulated folder-level statistics.
        file_entries: List of tuples containing file path and diagnostic counts.
        rule_file_counts: Mapping of diagnostic rules to file occurrence counters.
    """

    run_summary: dict[RunId, SummaryRunEntry]
    severity_totals: Counter[SeverityLevel]
    rule_totals: Counter[str]
    category_totals: Counter[CategoryKey]
    folder_stats: _FolderAccumulators
    file_entries: list[tuple[str, int, int, int]]
    rule_file_counts: dict[str, Counter[str]]


@dataclass(slots=True)
class _HotspotPayload:
    """Container for hotspot data used in dashboard tabs.

    Attributes:
        top_rules: Top diagnostic rules by occurrence count.
        top_folders: Top folders by diagnostic count.
        top_files: Top files by diagnostic count.
        rule_files: Mapping of diagnostic rules to affected files with counts.
    """

    top_rules: CountsByRule
    top_folders: list[SummaryFolderEntry]
    top_files: list[SummaryFileEntry]
    rule_files: dict[str, list[RulePathEntry]]


def _coerce_status_key(value: object) -> ReadinessStatus:
    if isinstance(value, ReadinessStatus):
        return value
    if isinstance(value, str):
        try:
            return ReadinessStatus.from_str(value)
        except ValueError as exc:
            msg = "readiness.strict"
            raise DashboardTypeError(msg, "a known readiness status") from exc
    msg = "readiness.strict"
    raise DashboardTypeError(msg, "a known readiness status")


def _maybe_severity_level(value: object) -> SeverityLevel | None:
    if isinstance(value, SeverityLevel):
        return value
    if isinstance(value, str):
        try:
            return SeverityLevel.from_str(value)
        except ValueError:
            return None
    return None


def _require_category_key(value: object, context: str) -> CategoryKey:
    category = coerce_category_key(value)
    if category is None:
        raise DashboardTypeError(context, "known readiness category")
    return category


class DashboardTypeError(RatchetrTypeError):
    """Raised when dashboard data has an unexpected shape.

    This exception is raised during dashboard data processing when the manifest
    or summary data does not conform to expected structure or types.

    Attributes:
        context: The location or field where the type error occurred.
        expected: Description of the expected type or format.
    """

    def __init__(self, context: str, expected: str) -> None:
        """Initialize the DashboardTypeError.

        Args:
            context: The location or field where the type error occurred.
            expected: Description of the expected type or format.
        """
        self.context = context
        self.expected = expected
        super().__init__(f"{context} must be {expected}")


def _coerce_rel_paths(values: Sequence[str]) -> list[RelPath]:
    return [RelPath(str(item)) for item in values if str(item)]


def load_manifest(path: Path) -> ManifestData:
    """Load and parse a manifest file from disk.

    Args:
        path: Path to the manifest JSON file.

    Returns:
        Parsed manifest data structure containing type checking runs and diagnostics.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    return load_manifest_data(raw)


def _collect_readiness(folder_entries: Sequence[ReadinessEntry]) -> ReadinessPayload:
    return compute_readiness(folder_entries)


def _empty_readiness_tab() -> ReadinessTab:
    strict_defaults: dict[ReadinessStatus, list[dict[str, JSONValue]]] = {status: [] for status in ReadinessStatus}
    return cast("ReadinessTab", {"strict": strict_defaults, "options": {}})


def _coerce_readiness_entries(value: object, context: str) -> list[dict[str, JSONValue]]:
    if value is None:
        return []
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        raise DashboardTypeError(context, "a sequence of mappings")
    entries: list[dict[str, JSONValue]] = []
    for index, entry in enumerate(cast("Sequence[object]", value)):
        if not isinstance(entry, Mapping):
            msg = f"{context}[{index}]"
            raise DashboardTypeError(msg, "a mapping")
        entries.append(coerce_mapping(cast("Mapping[object, object]", entry)))
    return entries


def _coerce_run_entries(manifest: ManifestData) -> list[dict[str, JSONValue]]:
    runs_raw = manifest.get("runs")
    if not isinstance(runs_raw, Sequence):
        return []
    entries: list[dict[str, JSONValue]] = [
        coerce_mapping(cast("Mapping[object, object]", item))
        for item in cast("Sequence[object]", runs_raw)
        if isinstance(item, Mapping)
    ]
    return entries


def _prepare_run_payload(
    run: Mapping[str, JSONValue],
) -> tuple[RunId, dict[str, JSONValue], dict[str, JSONValue], list[str]] | None:
    tool_obj = run.get("tool")
    mode_obj = run.get("mode")
    summary_obj = run.get("summary")
    if not isinstance(tool_obj, str) or not isinstance(mode_obj, str):
        return None
    summary_map = coerce_mapping(summary_obj)
    command_list = [str(part) for part in coerce_object_list(run.get("command"))]
    options_obj = run.get("engineOptions")
    options_map: dict[str, JSONValue] = (
        coerce_mapping(cast("Mapping[object, object]", options_obj)) if isinstance(options_obj, Mapping) else {}
    )
    return RunId(f"{tool_obj}:{mode_obj}"), summary_map, options_map, command_list


def _clean_optional_str(value: object) -> str | None:
    if isinstance(value, str):
        candidate = value.strip()
        return candidate or None
    return None


def _build_engine_options_payload(options_map: Mapping[str, JSONValue]) -> EngineOptionsEntry:
    profile = _clean_optional_str(options_map.get("profile"))
    config_file = _clean_optional_str(options_map.get("configFile"))
    plugin_args = coerce_str_list(options_map.get("pluginArgs", []))
    include_paths = _coerce_rel_paths(coerce_str_list(options_map.get("include", [])))
    exclude_paths = _coerce_rel_paths(coerce_str_list(options_map.get("exclude", [])))
    overrides = _parse_manifest_overrides(options_map.get("overrides", []))
    category_mapping = _parse_category_mapping(options_map.get("categoryMapping"))
    return {
        "profile": profile,
        "configFile": config_file,
        "pluginArgs": plugin_args,
        "include": include_paths,
        "exclude": exclude_paths,
        "overrides": clone_override_entries(overrides),
        "categoryMapping": category_mapping,
    }


def _parse_manifest_overrides(raw_overrides: object) -> list[OverrideEntry]:
    overrides: list[OverrideEntry] = []
    for override_obj in coerce_object_list(raw_overrides):
        if not isinstance(override_obj, Mapping):
            continue
        override_map = coerce_mapping(cast("Mapping[object, object]", override_obj))
        entry: OverrideEntry = {}
        path_value = override_map.get("path")
        if isinstance(path_value, str) and path_value:
            entry["path"] = path_value
        profile_value = override_map.get("profile")
        if isinstance(profile_value, str) and profile_value:
            entry["profile"] = profile_value
        plugin_args_value = coerce_str_list(override_map.get("pluginArgs", []))
        if plugin_args_value:
            entry["pluginArgs"] = plugin_args_value
        include_value = _coerce_rel_paths(coerce_str_list(override_map.get("include", [])))
        if include_value:
            entry["include"] = include_value
        exclude_value = _coerce_rel_paths(coerce_str_list(override_map.get("exclude", [])))
        if exclude_value:
            entry["exclude"] = exclude_value
        if entry:
            overrides.append(entry)
    return overrides


def _parse_category_mapping(raw_mapping: object) -> CategoryMapping:
    if not isinstance(raw_mapping, Mapping):
        return {}
    source: dict[str, JSONValue] = coerce_mapping(cast("Mapping[object, object]", raw_mapping))
    category_mapping: CategoryMapping = {}
    for key, values in source.items():
        category_key = coerce_category_key(key)
        if category_key is None:
            continue
        value_list = [
            str(item).strip() for item in coerce_object_list(values) if isinstance(item, str | int | float | bool)
        ]
        cleaned = [item for item in value_list if item]
        if cleaned:
            category_mapping[category_key] = cleaned
    return category_mapping


def _parse_severity_breakdown(summary_map: Mapping[str, JSONValue]) -> CountsBySeverity:
    breakdown_map = coerce_mapping(summary_map.get("severityBreakdown"))
    severity_breakdown: CountsBySeverity = {}
    for sev_key, value in breakdown_map.items():
        severity = _maybe_severity_level(sev_key)
        if severity is None:
            continue
        severity_breakdown[severity] = coerce_int(value)
    return severity_breakdown


def _parse_rule_counts(summary_map: Mapping[str, JSONValue]) -> CountsByRule:
    return {key: coerce_int(value) for key, value in coerce_mapping(summary_map.get("ruleCounts")).items()}


def _parse_category_counts(summary_map: Mapping[str, JSONValue]) -> CountsByCategory:
    category_counts_map = coerce_mapping(summary_map.get("categoryCounts"))
    category_counts: CountsByCategory = {}
    for cat_key, value in category_counts_map.items():
        category = coerce_category_key(cat_key)
        if category is None:
            continue
        category_counts[category] = coerce_int(value)
    return category_counts


def _coerce_folder_entries(per_folder: object) -> list[dict[str, JSONValue]]:
    return [
        coerce_mapping(cast("Mapping[object, object]", entry))
        for entry in coerce_object_list(per_folder)
        if isinstance(entry, Mapping)
    ]


def _coerce_file_entries(per_file: object) -> list[dict[str, JSONValue]]:
    return _coerce_folder_entries(per_file)


def _update_folder_metrics(
    folder_entries: Sequence[Mapping[str, JSONValue]],
    folder_stats: _FolderAccumulators,
) -> None:
    for folder in folder_entries:
        path_obj = folder.get("path")
        if not isinstance(path_obj, str) or not path_obj:
            continue
        path = path_obj
        errors = coerce_int(folder.get("errors"))
        warnings = coerce_int(folder.get("warnings"))
        information = coerce_int(folder.get("information"))
        folder_stats.totals[path]["errors"] += errors
        folder_stats.totals[path]["warnings"] += warnings
        folder_stats.totals[path]["information"] += information
        folder_stats.counts[path] += 1
        code_counts_map = coerce_mapping(folder.get("codeCounts"))
        for code, count in code_counts_map.items():
            folder_stats.code_totals[path][code] += coerce_int(count)
        category_counts_map = coerce_mapping(folder.get("categoryCounts"))
        for raw_category, count in category_counts_map.items():
            category_key = coerce_category_key(raw_category)
            if category_key is None:
                continue
            folder_stats.category_totals[path][category_key] += coerce_int(count)
        rec_values = coerce_object_list(folder.get("recommendations"))
        for rec in rec_values:
            rec_text = rec.strip() if isinstance(rec, str) else str(rec).strip()
            if rec_text:
                folder_stats.recommendations[path].add(rec_text)


def _update_file_metrics(
    per_file_entries: Sequence[Mapping[str, JSONValue]],
    file_entries: list[tuple[str, int, int, int]],
    rule_file_counts: dict[str, Counter[str]],
) -> None:
    for entry in per_file_entries:
        path_obj = entry.get("path")
        if not isinstance(path_obj, str) or not path_obj:
            continue
        errors = coerce_int(entry.get("errors"))
        warnings = coerce_int(entry.get("warnings"))
        information = coerce_int(entry.get("information"))
        if not errors and not warnings:
            continue
        file_entries.append((path_obj, errors, warnings, information))
        diagnostics = coerce_object_list(entry.get("diagnostics"))
        if not diagnostics:
            continue
        per_file_rule_counts: Counter[str] = Counter()
        for diag in diagnostics:
            if not isinstance(diag, Mapping):
                continue
            diag_map = coerce_mapping(cast("Mapping[object, object]", diag))
            code_obj = diag_map.get("code")
            code = str(code_obj).strip() if isinstance(code_obj, str) else ""
            if code:
                per_file_rule_counts[code] += 1
        for rule, count in per_file_rule_counts.items():
            rule_file_counts[rule][path_obj] += count


def _consume_run(run: Mapping[str, JSONValue], *, state: _SummaryState) -> None:
    payload = _prepare_run_payload(run)
    if payload is None:
        return
    run_id, summary_map, options_map, command_list = payload
    engine_options = _build_engine_options_payload(options_map)
    run_entry: SummaryRunEntry = {
        "command": command_list,
        "errors": coerce_int(summary_map.get("errors")),
        "warnings": coerce_int(summary_map.get("warnings")),
        "information": coerce_int(summary_map.get("information")),
        "total": coerce_int(summary_map.get("total")),
        "engineOptions": engine_options,
    }
    severity_breakdown = _parse_severity_breakdown(summary_map)
    rule_counts = _parse_rule_counts(summary_map)
    category_counts = _parse_category_counts(summary_map)
    if severity_breakdown:
        run_entry["severityBreakdown"] = severity_breakdown
    if rule_counts:
        run_entry["ruleCounts"] = rule_counts
    if category_counts:
        run_entry["categoryCounts"] = category_counts
    tool_summary_obj = run.get("toolSummary")
    if isinstance(tool_summary_obj, Mapping) and tool_summary_obj:
        run_entry["toolSummary"] = cast(
            "ToolSummary",
            {
                "errors": coerce_int(tool_summary_obj.get("errors")),
                "warnings": coerce_int(tool_summary_obj.get("warnings")),
                "information": coerce_int(tool_summary_obj.get("information")),
                "total": coerce_int(tool_summary_obj.get("total")),
            },
        )

    state.run_summary[run_id] = run_entry
    state.severity_totals.update(severity_breakdown)
    state.rule_totals.update(rule_counts)
    state.category_totals.update(category_counts)

    folder_entries = _coerce_folder_entries(run.get("perFolder"))
    _update_folder_metrics(folder_entries, state.folder_stats)
    file_entries_raw = _coerce_file_entries(run.get("perFile"))
    _update_file_metrics(file_entries_raw, state.file_entries, state.rule_file_counts)


def _create_summary_state() -> _SummaryState:
    return _SummaryState(
        run_summary={},
        severity_totals=Counter(),
        rule_totals=Counter(),
        category_totals=Counter(),
        folder_stats=_FolderAccumulators(
            totals=defaultdict(Counter),
            counts=defaultdict(int),
            code_totals=defaultdict(Counter),
            category_totals=defaultdict(Counter),
            recommendations=defaultdict(set),
        ),
        file_entries=[],
        rule_file_counts=defaultdict(Counter),
    )


def _build_readiness_section(folder_entries: Sequence[ReadinessEntry]) -> ReadinessTab:
    readiness_raw = _collect_readiness(folder_entries)
    try:
        return _validate_readiness_tab(cast("Mapping[object, object]", readiness_raw))
    except ValueError as exc:
        logger.warning(
            "Discarding invalid readiness payload: %s",
            exc,
            extra=structured_extra(component=LogComponent.DASHBOARD),
        )
        return _empty_readiness_tab()


def _select_top_folders(folder_stats: _FolderAccumulators) -> list[tuple[str, Counter[str]]]:
    return sorted(
        folder_stats.totals.items(),
        key=lambda item: (-item[1]["errors"], -item[1]["warnings"], item[0]),
    )[:25]


def _select_top_files(
    file_entries: Sequence[tuple[str, int, int, int]],
) -> list[tuple[str, int, int, int]]:
    return sorted(
        file_entries,
        key=lambda item: (-item[1], -item[2], -item[3], item[0]),
    )[:25]


def _build_top_folder_entries(
    top_folders: Sequence[tuple[str, Counter[str]]],
    folder_entries_full: Sequence[ReadinessEntry],
    folder_stats: _FolderAccumulators,
) -> list[SummaryFolderEntry]:
    folder_entry_lookup: dict[str, ReadinessEntry] = {entry["path"]: entry for entry in folder_entries_full}
    payload: list[SummaryFolderEntry] = []
    for path, counts in top_folders:
        folder_entry = folder_entry_lookup.get(path)
        code_counts: dict[str, int] = dict(folder_entry["codeCounts"]) if folder_entry else {}
        recommendations: list[str] = list(folder_entry["recommendations"]) if folder_entry else []
        payload.append(
            {
                "path": path,
                "errors": counts["errors"],
                "warnings": counts["warnings"],
                "information": counts["information"],
                "participatingRuns": folder_stats.counts[path],
                "codeCounts": code_counts,
                "recommendations": recommendations,
            },
        )
    return payload


def _build_top_file_entries(
    top_files: Sequence[tuple[str, int, int, int]],
) -> list[SummaryFileEntry]:
    return [
        {"path": path, "errors": errors, "warnings": warnings, "information": information}
        for path, errors, warnings, information in top_files
    ]


def _build_rule_files_payload(
    rule_file_counts: Mapping[str, Counter[str]],
) -> dict[str, list[RulePathEntry]]:
    payload: dict[str, list[RulePathEntry]] = {}
    for rule, occurrences in sorted(rule_file_counts.items()):
        entries: list[RulePathEntry] = [
            RulePathEntry(path=file_path, count=int(count)) for file_path, count in occurrences.most_common(10)
        ]
        payload[rule] = entries
    return payload


def _build_top_rules(rule_totals: Counter[str]) -> CountsByRule:
    return dict(rule_totals.most_common(20))


def _compose_tabs_payload(
    *,
    run_summary: dict[RunId, SummaryRunEntry],
    severity_totals: Counter[SeverityLevel],
    category_totals: Counter[CategoryKey],
    readiness_tab: ReadinessTab,
    hotspots: _HotspotPayload,
) -> SummaryTabs:
    return {
        TAB_KEY_OVERVIEW: {
            "severityTotals": dict(severity_totals),
            "categoryTotals": dict(category_totals),
            "runSummary": run_summary,
        },
        TAB_KEY_ENGINES: {
            "runSummary": run_summary,
        },
        TAB_KEY_HOTSPOTS: {
            "topRules": hotspots.top_rules,
            "topFolders": hotspots.top_folders,
            "topFiles": hotspots.top_files,
            "ruleFiles": hotspots.rule_files,
        },
        TAB_KEY_READINESS: readiness_tab,
        TAB_KEY_RUNS: {
            "runSummary": run_summary,
        },
    }


def _extract_metadata(manifest: ManifestData) -> tuple[str, str]:
    generated_at_value = manifest.get("generatedAt")
    project_root_value = manifest.get("projectRoot")
    generated_at = generated_at_value if isinstance(generated_at_value, str) else ""
    project_root = project_root_value if isinstance(project_root_value, str) else ""
    return generated_at, project_root


def _validate_readiness_tab(raw: Mapping[object, object]) -> ReadinessTab:
    strict_raw = raw.get("strict")
    if not isinstance(strict_raw, Mapping):
        msg = "readiness.strict"
        raise DashboardTypeError(msg, "a mapping")
    strict_map = coerce_mapping(cast("Mapping[object, object]", strict_raw))
    strict_section: dict[ReadinessStatus, list[dict[str, JSONValue]]] = {status: [] for status in ReadinessStatus}
    for key, value in strict_map.items():
        status = _coerce_status_key(key)
        strict_section[status] = _coerce_readiness_entries(
            value,
            f"readiness.strict.{status.value}",
        )

    options_raw = raw.get("options")
    if not isinstance(options_raw, Mapping):
        msg = "readiness.options"
        raise DashboardTypeError(msg, "a mapping")
    options_map = coerce_mapping(cast("Mapping[object, object]", options_raw))
    options_section = _build_readiness_options(options_map)

    return cast(
        "ReadinessTab",
        {
            "strict": strict_section,
            "options": options_section,
        },
    )


def _build_readiness_options(options_map: dict[str, JSONValue]) -> dict[CategoryKey, ReadinessOptionsPayload]:
    options_section: dict[CategoryKey, ReadinessOptionsPayload] = {}
    for category_key_raw, bucket_obj in options_map.items():
        if not isinstance(bucket_obj, Mapping):
            msg = f"readiness.options[{category_key_raw!r}]"
            raise DashboardTypeError(msg, "a mapping")
        bucket_map = coerce_mapping(cast("Mapping[object, object]", bucket_obj))
        threshold_value = bucket_map.get("threshold")
        if threshold_value is not None and not isinstance(threshold_value, int):
            msg = f"readiness.options[{category_key_raw!r}].threshold"
            raise DashboardTypeError(
                msg,
                "an integer",
            )
        threshold = threshold_value if isinstance(threshold_value, int) else DEFAULT_CLOSE_THRESHOLD
        buckets_obj = bucket_map.get("buckets")
        if not isinstance(buckets_obj, Mapping):
            msg = f"readiness.options[{category_key_raw!r}].buckets"
            raise DashboardTypeError(
                msg,
                "a mapping",
            )
        buckets_map = coerce_mapping(cast("Mapping[object, object]", buckets_obj))
        options_bucket = ReadinessOptions(threshold=threshold)
        for status_key, entries in buckets_map.items():
            status = _coerce_status_key(status_key)
            parsed_entries = _coerce_readiness_entries(
                entries,
                f"readiness.options[{category_key_raw!r}].{status.value}",
            )
            for entry in cast("list[ReadinessOptionEntry]", parsed_entries):
                options_bucket.add_entry(status, entry)
        category_key = _require_category_key(
            category_key_raw,
            f"readiness.options[{category_key_raw!r}]",
        )
        options_section[category_key] = options_bucket.to_payload()
    return options_section


def build_summary(manifest: ManifestData) -> SummaryData:
    """Build a comprehensive dashboard summary from manifest data.

    This function aggregates diagnostic data from multiple type checking runs,
    computes readiness metrics, identifies hotspots, and structures all data
    for dashboard rendering.

    Args:
        manifest: Parsed manifest data containing type checking run results.

    Returns:
        Structured summary data ready for rendering in HTML or Markdown format.
        Includes overview metrics, run summaries, hotspots, and readiness analysis.
    """
    state = _create_summary_state()
    for run in _coerce_run_entries(manifest):
        _consume_run(run, state=state)

    folder_entries_full = state.folder_stats.build_entries()
    readiness_tab = _build_readiness_section(folder_entries_full)
    top_rules_dict = _build_top_rules(state.rule_totals)
    top_folders_list = _build_top_folder_entries(
        _select_top_folders(state.folder_stats),
        folder_entries_full,
        state.folder_stats,
    )
    top_files_list = _build_top_file_entries(_select_top_files(state.file_entries))
    rule_files_payload = _build_rule_files_payload(state.rule_file_counts)
    hotspots = _HotspotPayload(
        top_rules=top_rules_dict,
        top_folders=top_folders_list,
        top_files=top_files_list,
        rule_files=rule_files_payload,
    )
    tabs_payload = _compose_tabs_payload(
        run_summary=state.run_summary,
        severity_totals=state.severity_totals,
        category_totals=state.category_totals,
        readiness_tab=readiness_tab,
        hotspots=hotspots,
    )
    generated_at, project_root = _extract_metadata(manifest)

    return cast(
        "SummaryData",
        {
            "generatedAt": generated_at,
            "projectRoot": project_root,
            "runSummary": state.run_summary,
            "severityTotals": dict(state.severity_totals),
            "categoryTotals": dict(state.category_totals),
            "topRules": top_rules_dict,
            "topFolders": top_folders_list,
            "topFiles": top_files_list,
            "ruleFiles": rule_files_payload,
            "tabs": tabs_payload,
        },
    )


SummaryTabsKeys = SummaryTabName
