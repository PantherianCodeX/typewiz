from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast

from typewiz.core.model_types import OverrideEntry, ReadinessStatus, SeverityLevel, SummaryTabName
from typewiz.core.summary_types import (
    ReadinessOptionsPayload,
    ReadinessStrictEntry,
    ReadinessTab,
    SummaryData,
)
from typewiz.data_validation import coerce_mapping
from typewiz.override_utils import format_overrides_block
from typewiz.readiness.compute import CATEGORY_LABELS


def _materialise_dict_list(values: object) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes, bytearray)):
        return result
    for entry in cast(Sequence[object], values):
        if isinstance(entry, Mapping):
            entry_map = coerce_mapping(cast(Mapping[object, object], entry))
            result.append(dict(entry_map.items()))
    return result


def _format_entry_list(entries: Sequence[dict[str, object]], limit: int = 8) -> str:
    if not entries:
        return "—"
    paths = [f"`{entry['path']}`" for entry in entries[:limit]]
    if len(entries) > limit:
        paths.append(f"… +{len(entries) - limit} more")
    return ", ".join(paths)


def _empty_readiness_tab() -> ReadinessTab:
    strict_defaults: dict[ReadinessStatus, list[ReadinessStrictEntry]] = {
        status: [] for status in ReadinessStatus
    }
    return {"strict": strict_defaults, "options": {}}


def render_markdown(summary: SummaryData) -> str:
    tabs = summary["tabs"]
    overview = tabs[SummaryTabName.OVERVIEW.value]
    run_summary = overview["runSummary"]
    severity = overview["severityTotals"]
    hotspots = tabs[SummaryTabName.HOTSPOTS.value]

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
                f"- Errors: {severity.get(SeverityLevel.ERROR, 0)}",
                f"- Warnings: {severity.get(SeverityLevel.WARNING, 0)}",
                f"- Information: {severity.get(SeverityLevel.INFORMATION, 0)}",
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

    rule_files = hotspots.get("ruleFiles", {})
    if rule_files:
        lines.extend(
            [
                "",
                "#### Rule hotspots by file",
                "",
            ],
        )
        for rule, rule_entries in rule_files.items():
            formatted = ", ".join(
                f"`{entry.get('path', '<unknown>')}` ({entry.get('count', 0)})"
                for entry in rule_entries[:5]
            )
            lines.append(f"- `{rule}`: {formatted or '—'}")

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
    runs_tab = tabs[SummaryTabName.RUNS.value]
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
    try:
        readiness_section = tabs[SummaryTabName.READINESS.value]
    except KeyError:
        readiness_section = _empty_readiness_tab()
    strict_section_raw = cast(
        dict[ReadinessStatus, list[dict[str, object]]], readiness_section.get("strict", {})
    )
    strict_ready_raw = strict_section_raw.get(ReadinessStatus.READY, [])
    strict_close_raw = strict_section_raw.get(ReadinessStatus.CLOSE, [])
    strict_blocked_raw = strict_section_raw.get(ReadinessStatus.BLOCKED, [])

    ready_entries = _materialise_dict_list(strict_ready_raw)
    close_entries = _materialise_dict_list(strict_close_raw)
    blocked_entries = _materialise_dict_list(strict_blocked_raw)

    lines.append(f"- Ready for strict typing: {_format_entry_list(ready_entries)}")
    lines.append(f"- Close to strict typing: {_format_entry_list(close_entries)}")
    lines.append(f"- Blocked folders: {_format_entry_list(blocked_entries)}")

    readiness_options_raw = cast(
        dict[str, ReadinessOptionsPayload], readiness_section.get("options", {})
    )
    if readiness_options_raw:
        lines.extend(["", "#### Per-option readiness"])
        label_lookup = cast(dict[str, str], CATEGORY_LABELS)
        for category, buckets_obj in readiness_options_raw.items():
            label_key: str = str(category)
            label = label_lookup.get(label_key, label_key)
            threshold_value = buckets_obj.get("threshold", 0)
            lines.append(f"- **{label}** (≤{threshold_value} to be close):")
            bucket_map = buckets_obj.get("buckets", {})
            for status in ReadinessStatus:
                entries = _materialise_dict_list(bucket_map.get(status, ()))
                lines.append(f"  - {status.value.title()}: {_format_entry_list(entries)}")

    lines.append("")
    return "\n".join(lines)
