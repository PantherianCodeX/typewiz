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

"""Markdown rendering module for ratchetr dashboards.

This module provides functionality to render dashboard summary data as formatted
Markdown documents. The output includes overview metrics, run summaries, engine
details, hotspot analysis, readiness metrics, and run logs in a readable text format.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, cast

from ratchetr.common.override_utils import format_overrides_block
from ratchetr.config.validation import coerce_int, coerce_mapping, coerce_object_list
from ratchetr.core.model_types import OverrideEntry, ReadinessStatus, SeverityLevel
from ratchetr.core.summary_types import (
    TAB_KEY_HOTSPOTS,
    TAB_KEY_OVERVIEW,
    TAB_KEY_READINESS,
    TAB_KEY_RUNS,
)
from ratchetr.readiness.compute import CATEGORY_LABELS

if TYPE_CHECKING:
    from ratchetr.core.summary_types import (
        ReadinessOptionsPayload,
        ReadinessStrictEntry,
        ReadinessTab,
        SummaryData,
        SummaryRunEntry,
    )
    from ratchetr.core.type_aliases import RunId


def _materialise_dict_list(values: object) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes, bytearray)):
        return result
    for entry in cast("Sequence[object]", values):
        if isinstance(entry, Mapping):
            entry_map = coerce_mapping(cast("Mapping[object, object]", entry))
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
    strict_defaults: dict[ReadinessStatus, list[ReadinessStrictEntry]] = {status: [] for status in ReadinessStatus}
    return {"strict": strict_defaults, "options": {}}


def _md_header(summary: SummaryData) -> list[str]:
    return [
        "# ratchetr Dashboard",
        "",
        f"- Generated at: {summary['generatedAt']}",
        f"- Project root: `{summary['projectRoot']}`",
    ]


def _md_overview(severity: Mapping[SeverityLevel, int]) -> list[str]:
    if not severity:
        return []
    return [
        "",
        "## Overview",
        "",
        f"- Errors: {severity.get(SeverityLevel.ERROR, 0)}",
        f"- Warnings: {severity.get(SeverityLevel.WARNING, 0)}",
        f"- Information: {severity.get(SeverityLevel.INFORMATION, 0)}",
    ]


def _md_run_summary(run_summary: Mapping[RunId, SummaryRunEntry]) -> list[str]:
    lines = [
        "",
        "### Run summary",
        "",
        "| Run | Errors | Warnings | Information | Command |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    if not run_summary:
        lines.append("| _No runs recorded_ | 0 | 0 | 0 | — |")
        return lines
    for key, data in run_summary.items():
        dm = coerce_mapping(cast("Mapping[object, object]", data))
        cmd = " ".join(str(part) for part in coerce_object_list(dm.get("command")))
        row = f"| `{key}` | {dm.get('errors', 0)} | {dm.get('warnings', 0)} | {dm.get('information', 0)} | `{cmd}` |"
        lines.append(row)
    return lines


# ignore JUSTIFIED: renderer builds full table; splitting would duplicate traversal
def _md_engine_details(run_summary: Mapping[RunId, SummaryRunEntry]) -> list[str]:  # noqa: PLR0914, FIX002, TD003  # TODO@PantherianCodeX: Break into sub-renderers per section to trim locals
    lines = ["", "### Engine details"]
    if not run_summary:
        lines.append("- No engine data available")
        return lines
    for key, data in run_summary.items():
        dm = coerce_mapping(cast("Mapping[object, object]", data))
        options_obj = dm.get("engineOptions")
        options = (
            coerce_mapping(cast("Mapping[object, object]", options_obj)) if isinstance(options_obj, Mapping) else {}
        )
        profile = str(options.get("profile") or "—")
        config_file = str(options.get("configFile") or "—")
        plugin_args_list = [str(a) for a in coerce_object_list(options.get("pluginArgs"))]
        plugin_args = ", ".join(f"`{arg}`" for arg in plugin_args_list) or "—"
        include_list = [str(p) for p in coerce_object_list(options.get("include"))]
        include = ", ".join(f"`{p}`" for p in include_list) or "—"
        exclude_list = [str(p) for p in coerce_object_list(options.get("exclude"))]
        exclude = ", ".join(f"`{p}`" for p in exclude_list) or "—"
        lines.extend(
            [
                "",
                f"#### `{key}`",
                "",
                f"- Profile: {profile}",
                f"- Config file: {config_file}",
                f"- Plugin args: {plugin_args}",
                f"- Include paths: {include}",
                f"- Exclude paths: {exclude}",
            ],
        )
        tool_totals_obj = dm.get("toolSummary")
        if isinstance(tool_totals_obj, Mapping):
            tool_totals = coerce_mapping(cast("Mapping[object, object]", tool_totals_obj))
            t_errors = coerce_int(tool_totals.get("errors"))
            t_warnings = coerce_int(tool_totals.get("warnings"))
            t_info = coerce_int(tool_totals.get("information"))
            t_total = coerce_int(tool_totals.get("total")) or (t_errors + t_warnings + t_info)
            p_errors = coerce_int(dm.get("errors"))
            p_warnings = coerce_int(dm.get("warnings"))
            p_info = coerce_int(dm.get("information"))
            p_total = coerce_int(dm.get("total")) or (p_errors + p_warnings + p_info)
            mismatch = t_errors != p_errors or t_warnings != p_warnings or t_total != p_total
            mismatch_text = (
                f" (mismatch vs parsed: {p_errors}/{p_warnings}/{p_info} total={p_total})" if mismatch else ""
            )
            lines.append(
                (
                    f"- Tool totals: errors={t_errors}, warnings={t_warnings}, "
                    f"information={t_info}, total={t_total}{mismatch_text}"
                ),
            )
        overrides_obj = options.get("overrides")
        overrides: list[OverrideEntry] = []
        for item in coerce_object_list(overrides_obj):
            if isinstance(item, Mapping):
                entry_map = coerce_mapping(cast("Mapping[object, object]", item))
                overrides.append(cast("OverrideEntry", dict(entry_map.items())))
        if overrides:
            lines.append("- Folder overrides:")
            lines.extend(format_overrides_block(overrides))
    return lines


def _md_hotspots(hotspots: Mapping[str, object], summary: SummaryData) -> list[str]:
    lines: list[str] = ["", "### Hotspots"]
    top_rules = cast("Mapping[str, int]", hotspots.get("topRules", summary.get("topRules", {})))
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

    rule_files = cast("Mapping[str, Sequence[Mapping[str, object]]]", hotspots.get("ruleFiles", {}))
    if rule_files:
        lines.extend(["", "#### Rule hotspots by file", ""])
        for rule, rule_entries in rule_files.items():
            formatted = ", ".join(
                f"`{entry.get('path', '<unknown>')}` ({entry.get('count', 0)})" for entry in rule_entries[:5]
            )
            lines.append(f"- `{rule}`: {formatted or '—'}")

    # Folders
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
        for folder in cast("Sequence[Mapping[str, object]]", top_folders):
            row = (
                f"| `{folder['path']}` | {folder['errors']} | {folder['warnings']} | "
                f"{folder['information']} | {folder['participatingRuns']} |"
            )
            lines.append(row)
    else:
        lines.append("| _No folder hotspots_ | 0 | 0 | 0 | 0 |")

    # Files
    top_files = hotspots.get("topFiles", [])
    lines.extend([
        "",
        "#### File hotspots",
        "",
        "| File | Errors | Warnings |",
        "| --- | ---: | ---: |",
    ])
    if top_files:
        for entry in cast("Sequence[Mapping[str, object]]", top_files):
            row = f"| `{entry['path']}` | {entry['errors']} | {entry['warnings']} |"
            lines.append(row)
    else:
        lines.append("| _No file hotspots_ | 0 | 0 |")
    return lines


def _md_run_logs(
    runs_tab: Mapping[str, object],
    run_summary: Mapping[RunId, SummaryRunEntry],
) -> list[str]:
    lines = ["", "### Run logs"]
    rd_obj = runs_tab.get("runSummary")
    run_details = cast("Mapping[RunId, SummaryRunEntry]", rd_obj) if isinstance(rd_obj, Mapping) else run_summary
    if not run_details:
        lines.append("- No runs recorded")
        return lines
    for key, data in run_details.items():
        dm = coerce_mapping(cast("Mapping[object, object]", data))
        breakdown = coerce_mapping(cast("Mapping[object, object]", dm.get("severityBreakdown")))
        lines.extend(
            [
                "",
                f"#### `{key}`",
                "",
                f"- Errors: {coerce_int(dm.get('errors'))}",
                f"- Warnings: {coerce_int(dm.get('warnings'))}",
                f"- Information: {coerce_int(dm.get('information'))}",
                f"- Total diagnostics: {coerce_int(dm.get('total'))}",
                f"- Severity breakdown: {breakdown or '{}'}",
            ],
        )
    return lines


def _md_readiness(tabs: Mapping[str, object]) -> list[str]:
    lines = ["", "### Readiness snapshot", ""]
    raw = tabs.get(TAB_KEY_READINESS)
    rs: ReadinessTab = cast("ReadinessTab", raw) if isinstance(raw, Mapping) else _empty_readiness_tab()
    strict_section_raw = cast("dict[ReadinessStatus, list[dict[str, object]]]", rs.get("strict", {}))
    ready_entries = _materialise_dict_list(strict_section_raw.get(ReadinessStatus.READY, []))
    close_entries = _materialise_dict_list(strict_section_raw.get(ReadinessStatus.CLOSE, []))
    blocked_entries = _materialise_dict_list(strict_section_raw.get(ReadinessStatus.BLOCKED, []))
    lines.extend((
        f"- Ready for strict typing: {_format_entry_list(ready_entries)}",
        f"- Close to strict typing: {_format_entry_list(close_entries)}",
        f"- Blocked folders: {_format_entry_list(blocked_entries)}",
    ))

    readiness_options_raw = cast("dict[str, ReadinessOptionsPayload]", rs.get("options", {}))
    if readiness_options_raw:
        lines.extend(["", "#### Per-option readiness", ""])
        label_lookup = cast("dict[str, str]", CATEGORY_LABELS)
        for category, buckets_obj in readiness_options_raw.items():
            label_key: str = str(category)
            label = label_lookup.get(label_key, label_key)
            threshold_value = buckets_obj.get("threshold", 0)
            lines.append(f"- **{label}** (≤{threshold_value} to be close):")
            bucket_map = buckets_obj.get("buckets", {})
            for status in ReadinessStatus:
                entries = _materialise_dict_list(bucket_map.get(status, ()))
                lines.append(f"  - {status.value.title()}: {_format_entry_list(entries)}")
    return lines


def render_markdown(summary: SummaryData) -> str:
    """Render dashboard summary data as a formatted Markdown document.

    This function generates a comprehensive Markdown report containing all dashboard
    information: severity totals, run summaries, engine configurations, diagnostic
    hotspots, readiness analysis, and detailed run logs. The output is suitable for
    viewing in text editors, version control diffs, or Markdown renderers.

    Args:
        summary: Complete dashboard summary data to render.

    Returns:
        Formatted Markdown document as a string with headers, tables, and lists.
    """
    tabs = summary["tabs"]
    overview = tabs[TAB_KEY_OVERVIEW]
    run_summary = overview["runSummary"]
    severity = overview["severityTotals"]
    hotspots = tabs[TAB_KEY_HOTSPOTS]

    lines: list[str] = []
    lines.extend(_md_header(summary))
    lines.extend(_md_overview(severity))
    lines.extend(_md_run_summary(run_summary))
    lines.extend(_md_engine_details(run_summary))
    lines.extend(_md_hotspots(hotspots, summary))
    lines.extend(_md_run_logs(tabs[TAB_KEY_RUNS], run_summary))
    lines.extend(_md_readiness(tabs))
    lines.append("")
    return "\n".join(lines)
