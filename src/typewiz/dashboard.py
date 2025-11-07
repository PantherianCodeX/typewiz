# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final, cast

from .data_validation import coerce_int, coerce_mapping, coerce_object_list, coerce_str_list
from .exceptions import TypewizTypeError
from .manifest_loader import load_manifest_data
from .model_types import CategoryMapping, OverrideEntry, ReadinessStatus, clone_override_entries
from .override_utils import format_overrides_block
from .readiness import (
    CATEGORY_LABELS,
    STATUS_VALUES,
    STATUSES,
    ReadinessEntry,
    ReadinessPayload,
    compute_readiness,
)
from .summary_types import (
    CountsByCategory,
    CountsByRule,
    CountsBySeverity,
    ReadinessTab,
    StatusKey,
    SummaryData,
    SummaryFileEntry,
    SummaryFolderEntry,
    SummaryRunEntry,
    SummaryTabs,
)
from .typed_manifest import ManifestData, SeverityStr, ToolSummary
from .utils import JSONValue

logger: logging.Logger = logging.getLogger("typewiz.dashboard")
_STATUS_KEY_SET: Final[frozenset[str]] = frozenset(STATUS_VALUES)


def _as_status_key(value: str) -> StatusKey:
    if value not in _STATUS_KEY_SET:
        raise DashboardTypeError("readiness.strict", "known readiness status")
    return cast(StatusKey, value)


class DashboardTypeError(TypewizTypeError):
    """Raised when dashboard data has an unexpected shape."""

    def __init__(self, context: str, expected: str) -> None:
        self.context = context
        self.expected = expected
        super().__init__(f"{context} must be {expected}")


def load_manifest(path: Path) -> ManifestData:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return load_manifest_data(raw)


def _collect_readiness(folder_entries: Sequence[ReadinessEntry]) -> ReadinessPayload:
    return compute_readiness(folder_entries)


def _empty_readiness_tab() -> ReadinessTab:
    strict_defaults: dict[StatusKey, list[dict[str, JSONValue]]] = {
        _as_status_key(status_value): [] for status_value in STATUS_VALUES
    }
    return cast(
        "ReadinessTab",
        {
            "strict": strict_defaults,
            "options": {},
        },
    )


def _coerce_readiness_entries(value: object, context: str) -> list[dict[str, JSONValue]]:
    if value is None:
        return []
    if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
        raise DashboardTypeError(context, "a sequence of mappings")
    entries: list[dict[str, JSONValue]] = []
    for index, entry in enumerate(cast("Sequence[object]", value)):
        if not isinstance(entry, Mapping):
            raise DashboardTypeError(f"{context}[{index}]", "a mapping")
        entries.append(coerce_mapping(cast("Mapping[object, object]", entry)))
    return entries


def _validate_readiness_tab(raw: Mapping[str, object]) -> ReadinessTab:
    strict_raw = raw.get("strict")
    if not isinstance(strict_raw, Mapping):
        raise DashboardTypeError("readiness.strict", "a mapping")
    strict_map = coerce_mapping(cast("Mapping[object, object]", strict_raw))
    strict_section: dict[StatusKey, list[dict[str, JSONValue]]] = {}
    for status in STATUSES:
        key = _as_status_key(status.value)
        strict_section[key] = _coerce_readiness_entries(
            strict_map.get(key),
            f"readiness.strict.{key}",
        )

    options_raw = raw.get("options")
    if not isinstance(options_raw, Mapping):
        raise DashboardTypeError("readiness.options", "a mapping")
    options_map = coerce_mapping(cast("Mapping[object, object]", options_raw))
    options_section: dict[str, dict[str, object]] = {}
    for category, bucket_obj in options_map.items():
        if not isinstance(bucket_obj, Mapping):
            raise DashboardTypeError(f"readiness.options[{category!r}]", "a mapping")
        bucket_map = coerce_mapping(cast("Mapping[object, object]", bucket_obj))
        status_entries: dict[StatusKey, list[dict[str, JSONValue]]] = {}
        for status in STATUSES:
            key = _as_status_key(status.value)
            if key in bucket_map:
                status_entries[key] = _coerce_readiness_entries(
                    bucket_map.get(key),
                    f"readiness.options[{category!r}].{key}",
                )
        validated_bucket: dict[str, object] = {}
        for key, entries in status_entries.items():
            validated_bucket[key] = entries
        threshold_value = bucket_map.get("threshold")
        if threshold_value is not None:
            if isinstance(threshold_value, int):
                validated_bucket["threshold"] = threshold_value
            else:
                raise DashboardTypeError(f"readiness.options[{category!r}].threshold", "an integer")
        options_section[str(category)] = validated_bucket

    return cast(
        "ReadinessTab",
        {
            "strict": strict_section,
            "options": options_section,
        },
    )


def build_summary(manifest: ManifestData) -> SummaryData:
    runs_raw = manifest.get("runs")
    run_entries: list[dict[str, JSONValue]] = (
        [
            coerce_mapping(cast("Mapping[object, object]", item))
            for item in cast("Sequence[object]", runs_raw)
            if isinstance(item, Mapping)
        ]
        if isinstance(runs_raw, Sequence)
        else []
    )
    run_summary: dict[str, SummaryRunEntry] = {}
    folder_totals: dict[str, Counter[str]] = defaultdict(Counter)
    folder_counts: dict[str, int] = defaultdict(int)
    folder_code_totals: dict[str, Counter[str]] = defaultdict(Counter)
    folder_recommendations: dict[str, set[str]] = defaultdict(set)
    file_entries: list[tuple[str, int, int]] = []
    severity_totals: Counter[SeverityStr] = Counter()
    rule_totals: Counter[str] = Counter()
    category_totals: Counter[str] = Counter()
    folder_category_totals: dict[str, Counter[str]] = defaultdict(Counter)

    for run in run_entries:
        tool_obj = run.get("tool")
        mode_obj = run.get("mode")
        if not isinstance(tool_obj, str) or not isinstance(mode_obj, str):
            continue
        summary_obj = run.get("summary")
        if not isinstance(summary_obj, Mapping):
            continue
        summary_map: dict[str, JSONValue] = coerce_mapping(
            cast("Mapping[object, object]", summary_obj),
        )
        command_list = [str(part) for part in coerce_object_list(run.get("command"))]
        options_obj = run.get("engineOptions")
        options_map: dict[str, JSONValue] = (
            coerce_mapping(cast("Mapping[object, object]", options_obj))
            if isinstance(options_obj, Mapping)
            else {}
        )

        profile_obj = options_map.get("profile")
        profile = str(profile_obj).strip() if isinstance(profile_obj, str) else None
        if not profile:
            profile = None
        config_obj = options_map.get("configFile")
        config_file = str(config_obj).strip() if isinstance(config_obj, str) else None
        if not config_file:
            config_file = None
        plugin_args = coerce_str_list(options_map.get("pluginArgs", []))
        include_paths = coerce_str_list(options_map.get("include", []))
        exclude_paths = coerce_str_list(options_map.get("exclude", []))
        overrides: list[OverrideEntry] = []
        overrides_raw = coerce_object_list(options_map.get("overrides", []))
        for override_obj in overrides_raw:
            if isinstance(override_obj, Mapping):
                override_map = coerce_mapping(cast(Mapping[object, object], override_obj))
                override_entry: OverrideEntry = {}
                path_value = override_map.get("path")
                if isinstance(path_value, str) and path_value:
                    override_entry["path"] = path_value
                profile_value = override_map.get("profile")
                if isinstance(profile_value, str) and profile_value:
                    override_entry["profile"] = profile_value
                plugin_args_value = coerce_str_list(override_map.get("pluginArgs", []))
                if plugin_args_value:
                    override_entry["pluginArgs"] = plugin_args_value
                include_value = coerce_str_list(override_map.get("include", []))
                if include_value:
                    override_entry["include"] = include_value
                exclude_value = coerce_str_list(override_map.get("exclude", []))
                if exclude_value:
                    override_entry["exclude"] = exclude_value
                overrides.append(override_entry)
        category_mapping_raw = options_map.get("categoryMapping")
        category_mapping: CategoryMapping = {}
        if isinstance(category_mapping_raw, Mapping):
            category_mapping_source: dict[str, JSONValue] = coerce_mapping(
                cast(Mapping[object, object], category_mapping_raw),
            )
            for key, values in category_mapping_source.items():
                key_str = str(key).strip()
                if not key_str:
                    continue
                value_list = [
                    str(item).strip()
                    for item in coerce_object_list(values)
                    if isinstance(item, str | int | float | bool)
                ]
                cleaned = [item for item in value_list if item]
                if cleaned:
                    category_mapping[key_str] = cleaned

        key = f"{tool_obj}:{mode_obj}"
        run_entry: SummaryRunEntry = {
            "command": command_list,
            "errors": coerce_int(summary_map.get("errors")),
            "warnings": coerce_int(summary_map.get("warnings")),
            "information": coerce_int(summary_map.get("information")),
            "total": coerce_int(summary_map.get("total")),
            "engineOptions": {
                "profile": profile,
                "configFile": config_file,
                "pluginArgs": plugin_args,
                "include": include_paths,
                "exclude": exclude_paths,
                "overrides": clone_override_entries(overrides),
                "categoryMapping": category_mapping,
            },
        }
        severity_breakdown_map = coerce_mapping(summary_map.get("severityBreakdown"))
        severity_breakdown: CountsBySeverity = {
            cast(SeverityStr, key): coerce_int(value)
            for key, value in severity_breakdown_map.items()
        }
        rule_counts: CountsByRule = {
            key: coerce_int(value)
            for key, value in coerce_mapping(summary_map.get("ruleCounts")).items()
        }
        category_counts: CountsByCategory = {
            key: coerce_int(value)
            for key, value in coerce_mapping(summary_map.get("categoryCounts")).items()
        }
        if severity_breakdown:
            run_entry["severityBreakdown"] = severity_breakdown
        if rule_counts:
            run_entry["ruleCounts"] = rule_counts
        if category_counts:
            run_entry["categoryCounts"] = category_counts

        tool_summary_obj = run.get("toolSummary")
        if isinstance(tool_summary_obj, Mapping) and tool_summary_obj:
            raw_tool_summary = cast(
                ToolSummary,
                {
                    "errors": coerce_int(tool_summary_obj.get("errors")),
                    "warnings": coerce_int(tool_summary_obj.get("warnings")),
                    "information": coerce_int(tool_summary_obj.get("information")),
                    "total": coerce_int(tool_summary_obj.get("total")),
                },
            )
            run_entry["toolSummary"] = raw_tool_summary
        run_summary[key] = run_entry
        severity_totals.update(severity_breakdown)
        rule_totals.update(rule_counts)
        category_totals.update(category_counts)

        per_folder_entries_raw = coerce_object_list(run.get("perFolder"))
        per_folder_entries: list[dict[str, JSONValue]] = [
            coerce_mapping(cast(Mapping[object, object], entry))
            for entry in per_folder_entries_raw
            if isinstance(entry, Mapping)
        ]
        for folder in per_folder_entries:
            path_obj = folder.get("path")
            if not isinstance(path_obj, str) or not path_obj:
                continue
            path = path_obj
            errors = coerce_int(folder.get("errors"))
            warnings = coerce_int(folder.get("warnings"))
            information = coerce_int(folder.get("information"))
            folder_totals[path]["errors"] += errors
            folder_totals[path]["warnings"] += warnings
            folder_totals[path]["information"] += information
            folder_counts[path] += 1
            code_counts_map = coerce_mapping(folder.get("codeCounts"))
            for code, count in code_counts_map.items():
                folder_code_totals[path][code] += coerce_int(count)
            category_counts_map = coerce_mapping(folder.get("categoryCounts"))
            for category, count in category_counts_map.items():
                folder_category_totals[path][category] += coerce_int(count)
            rec_values = coerce_object_list(folder.get("recommendations"))
            for rec in rec_values:
                rec_text = rec.strip() if isinstance(rec, str) else str(rec).strip()
                if rec_text:
                    folder_recommendations[path].add(rec_text)
        per_file_entries_raw = coerce_object_list(run.get("perFile"))
        per_file_entries: list[dict[str, JSONValue]] = [
            coerce_mapping(cast(Mapping[object, object], entry))
            for entry in per_file_entries_raw
            if isinstance(entry, Mapping)
        ]
        for entry in per_file_entries:
            path_obj = entry.get("path")
            if not isinstance(path_obj, str) or not path_obj:
                continue
            errors = coerce_int(entry.get("errors"))
            warnings = coerce_int(entry.get("warnings"))
            if not errors and not warnings:
                continue
            file_entries.append((path_obj, errors, warnings))

    folder_entries_full: list[ReadinessEntry] = []
    for path, counts in folder_totals.items():
        folder_entries_full.append(
            {
                "path": path,
                "errors": counts["errors"],
                "warnings": counts["warnings"],
                "information": counts["information"],
                "codeCounts": dict(folder_code_totals.get(path, {})),
                "categoryCounts": dict(folder_category_totals.get(path, {})),
                "recommendations": sorted(folder_recommendations.get(path, [])),
            },
        )

    top_folders = sorted(
        folder_totals.items(),
        key=lambda item: (-item[1]["errors"], -item[1]["warnings"], item[0]),
    )[:25]
    top_files = sorted(
        file_entries,
        key=lambda item: (-item[1], -item[2], item[0]),
    )[:25]
    readiness_raw = _collect_readiness(folder_entries_full)
    try:
        readiness_tab = _validate_readiness_tab(cast(Mapping[str, object], readiness_raw))
    except ValueError as exc:
        logger.warning("Discarding invalid readiness payload: %s", exc)
        readiness_tab = _empty_readiness_tab()

    top_rules_dict: CountsByRule = dict(rule_totals.most_common(20))
    folder_entry_lookup: dict[str, ReadinessEntry] = {
        entry["path"]: entry for entry in folder_entries_full
    }
    top_folders_list: list[SummaryFolderEntry] = []
    for path, counts in top_folders:
        folder_entry = folder_entry_lookup.get(path)
        code_counts: dict[str, int] = dict(folder_entry["codeCounts"]) if folder_entry else {}
        recommendations: list[str] = list(folder_entry["recommendations"]) if folder_entry else []
        top_folders_list.append(
            {
                "path": path,
                "errors": counts["errors"],
                "warnings": counts["warnings"],
                "information": counts["information"],
                "participatingRuns": folder_counts[path],
                "codeCounts": code_counts,
                "recommendations": recommendations,
            },
        )
    top_files_list: list[SummaryFileEntry] = [
        {"path": path, "errors": errors, "warnings": warnings}
        for path, errors, warnings in top_files
    ]

    tabs_payload: SummaryTabs = {
        "overview": {
            "severityTotals": dict(severity_totals),
            "categoryTotals": dict(category_totals),
            "runSummary": run_summary,
        },
        "engines": {
            "runSummary": run_summary,
        },
        "hotspots": {
            "topRules": top_rules_dict,
            "topFolders": top_folders_list,
            "topFiles": top_files_list,
        },
        "readiness": readiness_tab,
        "runs": {
            "runSummary": run_summary,
        },
    }

    generated_at_value = manifest.get("generatedAt")
    project_root_value = manifest.get("projectRoot")
    generated_at = generated_at_value if isinstance(generated_at_value, str) else ""
    project_root = project_root_value if isinstance(project_root_value, str) else ""

    return cast(
        SummaryData,
        {
            "generatedAt": generated_at,
            "projectRoot": project_root,
            "runSummary": run_summary,
            "severityTotals": dict(severity_totals),
            "categoryTotals": dict(category_totals),
            "topRules": top_rules_dict,
            "topFolders": top_folders_list,
            "topFiles": top_files_list,
            "tabs": tabs_payload,
        },
    )


def render_markdown(summary: SummaryData) -> str:
    tabs = summary["tabs"]
    overview = tabs["overview"]
    run_summary = overview["runSummary"]
    severity = overview["severityTotals"]
    hotspots = tabs["hotspots"]

    lines: list[str] = [
        "# typewiz Dashboard",
        "",
        f"- Generated at: {summary['generatedAt']}",
        f"- Project root: `{summary['projectRoot']}`",
    ]

    if severity:
        lines.extend(
            [
                "",
                "## Overview",
                "",
                f"- Errors: {severity.get('error', 0)}",
                f"- Warnings: {severity.get('warning', 0)}",
                f"- Information: {severity.get('information', 0)}",
            ],
        )

    lines.extend(
        [
            "",
            "### Run summary",
            "",
            "| Run | Errors | Warnings | Information | Command |",
            "| --- | ---: | ---: | ---: | --- |",
        ],
    )
    for key, data in run_summary.items():
        cmd = " ".join(str(part) for part in data.get("command", []))
        lines.append(
            f"| `{key}` | {data.get('errors', 0)} | {data.get('warnings', 0)} | {data.get('information', 0)} | `{cmd}` |",
        )
    if not run_summary:
        lines.append("| _No runs recorded_ | 0 | 0 | 0 | — |")

    lines.extend(["", "### Engine details"])
    if run_summary:
        for key, data in run_summary.items():
            options = data.get("engineOptions", {})
            profile = options.get("profile") or "—"
            config_file = options.get("configFile") or "—"
            plugin_args = (
                ", ".join(f"`{arg}`" for arg in options.get("pluginArgs", []) or []) or "—"
            )
            include = ", ".join(f"`{path}`" for path in options.get("include", []) or []) or "—"
            exclude = ", ".join(f"`{path}`" for path in options.get("exclude", []) or []) or "—"
            lines.extend(
                [
                    "",
                    f"#### `{key}`",
                    f"- Profile: {profile}",
                    f"- Config file: {config_file}",
                    f"- Plugin args: {plugin_args}",
                    f"- Include paths: {include}",
                    f"- Exclude paths: {exclude}",
                ],
            )
            # If the raw tool totals are present, surface them for transparency.
            tool_totals = data.get("toolSummary")
            if isinstance(tool_totals, dict) and tool_totals:
                t_errors = int(tool_totals.get("errors", 0))
                t_warnings = int(tool_totals.get("warnings", 0))
                t_info = int(tool_totals.get("information", 0))
                t_total = int(tool_totals.get("total", t_errors + t_warnings + t_info))
                p_errors = int(data.get("errors", 0))
                p_warnings = int(data.get("warnings", 0))
                p_info = int(data.get("information", 0))
                p_total = int(data.get("total", p_errors + p_warnings + p_info))
                mismatch = t_errors != p_errors or t_warnings != p_warnings or t_total != p_total
                mismatch_note = (
                    f" (mismatch vs parsed: {p_errors}/{p_warnings}/{p_info} total={p_total})"
                    if mismatch
                    else ""
                )
                lines.append(
                    f"- Tool totals: errors={t_errors}, warnings={t_warnings}, information={t_info}, total={t_total}{mismatch_note}",
                )
            overrides: list[OverrideEntry] = options.get("overrides", []) or []
            if overrides:
                lines.append("- Folder overrides:")
                lines.extend(format_overrides_block(overrides))
    else:
        lines.append("- No engine data available")

    lines.extend(["", "### Hotspots"])
    top_rules = hotspots.get("topRules", summary.get("topRules", {}))
    if top_rules:
        lines.extend(
            [
                "",
                "#### Diagnostic rules",
                "",
                "| Rule | Count |",
                "| --- | ---: |",
            ],
        )
        lines.extend(f"| `{rule}` | {count} |" for rule, count in top_rules.items())
    else:
        lines.append("- No diagnostic rules recorded")

    top_folders = hotspots.get("topFolders", [])
    lines.extend(
        [
            "",
            "#### Folder hotspots",
            "",
            "| Folder | Errors | Warnings | Information | Runs |",
            "| --- | ---: | ---: | ---: | ---: |",
        ],
    )
    if top_folders:
        lines.extend(
            f"| `{folder['path']}` | {folder['errors']} | {folder['warnings']} | {folder['information']} | {folder['participatingRuns']} |"
            for folder in top_folders
        )
    else:
        lines.append("| _No folder hotspots_ | 0 | 0 | 0 | 0 |")

    top_files = hotspots.get("topFiles", [])
    lines.extend(
        [
            "",
            "#### File hotspots",
            "",
            "| File | Errors | Warnings |",
            "| --- | ---: | ---: |",
        ],
    )
    if top_files:
        lines.extend(
            f"| `{file_entry['path']}` | {file_entry['errors']} | {file_entry['warnings']} |"
            for file_entry in top_files
        )
    else:
        lines.append("| _No file hotspots_ | 0 | 0 |")

    lines.extend(["", "### Run logs"])
    runs_tab = tabs["runs"]
    run_details = runs_tab.get("runSummary", run_summary)
    if run_details:
        for key, data in run_details.items():
            breakdown = data.get("severityBreakdown", {})
            lines.extend(
                [
                    "",
                    f"#### `{key}`",
                    f"- Errors: {data.get('errors', 0)}",
                    f"- Warnings: {data.get('warnings', 0)}",
                    f"- Information: {data.get('information', 0)}",
                    f"- Total diagnostics: {data.get('total', 0)}",
                    f"- Severity breakdown: {breakdown or '{}'}",
                ],
            )
    else:
        lines.append("- No runs recorded")

    lines.extend(["", "### Readiness snapshot"])
    empty_readiness = _empty_readiness_tab()
    readiness_section = tabs.get("readiness") or empty_readiness
    strict_section_raw = readiness_section.get("strict", {})
    strict_ready_raw = strict_section_raw.get(ReadinessStatus.READY.value, [])
    strict_close_raw = strict_section_raw.get(ReadinessStatus.CLOSE.value, [])
    strict_blocked_raw = strict_section_raw.get(ReadinessStatus.BLOCKED.value, [])

    def _materialise_dict_list(values: object) -> list[dict[str, object]]:
        result: list[dict[str, object]] = []
        if not isinstance(values, Sequence) or isinstance(values, str | bytes | bytearray):
            return result
        for entry in cast(Sequence[object], values):
            if isinstance(entry, Mapping):
                entry_map = coerce_mapping(cast(Mapping[object, object], entry))
                result.append(dict(entry_map.items()))
        return result

    ready_entries = _materialise_dict_list(strict_ready_raw)
    close_entries = _materialise_dict_list(strict_close_raw)
    blocked_entries = _materialise_dict_list(strict_blocked_raw)

    def _format_entry_list(entries: Sequence[dict[str, object]], limit: int = 8) -> str:
        if not entries:
            return "—"
        paths = [f"`{entry['path']}`" for entry in entries[:limit]]
        if len(entries) > limit:
            paths.append(f"… +{len(entries) - limit} more")
        return ", ".join(paths)

    lines.append(f"- Ready for strict typing: {_format_entry_list(ready_entries)}")
    lines.append(f"- Close to strict typing: {_format_entry_list(close_entries)}")
    lines.append(f"- Blocked folders: {_format_entry_list(blocked_entries)}")

    readiness_options_raw = readiness_section.get("options", {})
    if readiness_options_raw:
        lines.extend(["", "#### Per-option readiness"])
        label_lookup = cast(dict[str, str], CATEGORY_LABELS)
        for category, buckets_obj in readiness_options_raw.items():
            buckets_dict = {status.value: buckets_obj.get(status.value) for status in STATUSES}
            buckets_dict["threshold"] = buckets_obj.get("threshold")
            label_key: str = str(category)
            label = label_lookup.get(label_key, label_key)
            threshold = buckets_dict.get("threshold")
            threshold_value = threshold if isinstance(threshold, int) else 0
            lines.append(f"- **{label}** (≤{threshold_value} to be close):")
            for status in STATUSES:
                entries = _materialise_dict_list(buckets_dict.get(status.value))
                lines.append(f"  - {status.value.title()}: {_format_entry_list(entries)}")

    lines.append("")
    return "\n".join(lines)
