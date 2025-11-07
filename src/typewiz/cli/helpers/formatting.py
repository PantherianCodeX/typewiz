# Copyright (c) 2024 PantherianCodeX
"""Formatting and presentation helpers for the Typewiz CLI."""

from __future__ import annotations

from collections.abc import Sequence

from typewiz.cli_helpers import (
    format_list as _legacy_format_list,
)
from typewiz.cli_helpers import (
    parse_summary_fields as _legacy_parse_summary_fields,
)
from typewiz.cli_helpers import (
    render_data_structure as _legacy_render_data_structure,
)
from typewiz.data_validation import coerce_int, coerce_mapping, coerce_object_list, coerce_str_list
from typewiz.error_codes import error_code_for
from typewiz.model_types import (
    DataFormat,
    HotspotKind,
    ReadinessLevel,
    ReadinessStatus,
    SummaryField,
    SummaryStyle,
    clone_override_entries,
)
from typewiz.override_utils import format_override_inline, override_detail_lines
from typewiz.readiness_views import ReadinessValidationError
from typewiz.readiness_views import collect_readiness_view as _collect_readiness_view
from typewiz.summary_types import SummaryData
from typewiz.types import RunResult

from .io import echo

SUMMARY_FIELD_CHOICES: set[SummaryField] = set(SummaryField)


def format_list(values: Sequence[str]) -> str:
    """Delegate to the historic ``typewiz.cli_helpers.format_list`` helper."""
    return _legacy_format_list(values)


def parse_summary_fields(
    raw: str | None,
    *,
    valid_fields: set[SummaryField] | None = None,
) -> list[SummaryField]:
    """Parse ``--summary-fields`` input, validating against allowable field names."""
    field_set = valid_fields if valid_fields is not None else SUMMARY_FIELD_CHOICES
    return _legacy_parse_summary_fields(raw, valid_fields=field_set)


def _print_run_summary(
    run: RunResult,
    *,
    fields: set[SummaryField],
    style: SummaryStyle,
) -> None:
    counts = run.severity_counts()
    summary = (
        f"errors={counts.get('error', 0)} "
        f"warnings={counts.get('warning', 0)} "
        f"info={counts.get('information', 0)}"
    )
    command = " ".join(run.command)
    header = f"[typewiz] {run.tool}:{run.mode} exit={run.exit_code} {summary} ({command})"

    detail_items: list[tuple[str, str]] = []

    expanded = style is not SummaryStyle.COMPACT
    if SummaryField.PROFILE in fields:
        if run.profile:
            detail_items.append(("profile", run.profile))
        elif expanded:
            detail_items.append(("profile", "—"))
    if SummaryField.CONFIG in fields:
        if run.config_file:
            detail_items.append(("config", str(run.config_file)))
        elif expanded:
            detail_items.append(("config", "—"))
    if SummaryField.PLUGIN_ARGS in fields:
        plugin_args = format_list(list(run.plugin_args))
        if plugin_args != "—" or expanded:
            detail_items.append(("plugin args", plugin_args))
    if SummaryField.PATHS in fields:
        include_paths = format_list(list(run.include))
        exclude_paths = format_list(list(run.exclude))
        if include_paths != "—" or expanded:
            detail_items.append(("include", include_paths))
        if exclude_paths != "—" or expanded:
            detail_items.append(("exclude", exclude_paths))
    if SummaryField.OVERRIDES in fields:
        overrides_data = clone_override_entries(run.overrides)
        if overrides_data:
            if expanded:
                for entry in overrides_data:
                    path, details = override_detail_lines(entry)
                    detail_items.append((f"override {path}", "; ".join(details)))
            else:
                short = [format_override_inline(entry) for entry in overrides_data]
                detail_items.append(("overrides", "; ".join(short)))

    if expanded and detail_items:
        echo(header)
        for label, value in detail_items:
            echo(f"           - {label}: {value}")
        return

    inline_parts = [f"{label}={value}" for label, value in detail_items]
    suffix = f" [{' '.join(inline_parts)}]" if inline_parts else ""
    echo(f"{header}{suffix}")


def print_summary(
    runs: Sequence[RunResult],
    fields: Sequence[SummaryField],
    style: SummaryStyle,
) -> None:
    """Render a human-friendly summary line for each run."""
    field_set = set(fields)
    for run in runs:
        _print_run_summary(run, fields=field_set, style=style)


def collect_readiness_view(
    summary: SummaryData,
    *,
    level: ReadinessLevel,
    statuses: Sequence[ReadinessStatus] | None,
    limit: int,
) -> dict[str, list[dict[str, object]]]:
    """Collect readiness data with consistent error handling."""
    try:
        return _collect_readiness_view(
            summary,
            level=level.value,
            statuses=statuses,
            limit=limit,
        )
    except ReadinessValidationError as exc:  # pragma: no cover - exercised via CLI tests
        code = error_code_for(exc)
        message = f"({code}) Invalid readiness data encountered: {exc}"
        raise SystemExit(message) from exc


def print_readiness_summary(
    summary: SummaryData,
    *,
    level: ReadinessLevel,
    statuses: Sequence[ReadinessStatus] | None,
    limit: int,
) -> None:
    """Print a readiness summary in the same shape as historic CLI output."""
    view = collect_readiness_view(summary, level=level, statuses=statuses, limit=limit)
    for status, entries in view.items():
        echo(f"[typewiz] readiness {level.value} status={status} (top {limit})")
        if not entries:
            echo("  <none>")
            continue
        for entry in entries:
            path = str(entry.get("path", "<unknown>"))
            count_key = "count" if level is ReadinessLevel.FOLDER else "diagnostics"
            count = coerce_int(entry.get(count_key))
            echo(f"  {path}: {count}")


def render_data(data: object, fmt: DataFormat) -> list[str]:
    """Render Python data for CLI output."""
    return _legacy_render_data_structure(data, fmt)


def query_overview(
    summary: SummaryData,
    *,
    include_categories: bool,
    include_runs: bool,
) -> dict[str, object]:
    """Build the payload for ``typewiz query overview``."""
    overview = summary["tabs"]["overview"]
    payload: dict[str, object] = {
        "generated_at": summary.get("generatedAt"),
        "project_root": summary.get("projectRoot"),
        "severity_totals": dict(overview.get("severityTotals", {})),
    }
    if include_categories:
        payload["category_totals"] = dict(overview.get("categoryTotals", {}))
    if include_runs:
        runs: list[dict[str, object]] = []
        for name, entry in overview.get("runSummary", {}).items():
            errors = int(entry.get("errors", 0) or 0)
            warnings = int(entry.get("warnings", 0) or 0)
            information = int(entry.get("information", 0) or 0)
            runs.append(
                {
                    "run": name,
                    "errors": errors,
                    "warnings": warnings,
                    "information": information,
                    "total": int(entry.get("total", errors + warnings + information) or 0),
                },
            )
        payload["runs"] = runs
    return payload


def query_hotspots(
    summary: SummaryData,
    *,
    kind: HotspotKind,
    limit: int,
) -> list[dict[str, object]]:
    """Build the payload for ``typewiz query hotspots``."""
    hotspots = summary["tabs"]["hotspots"]
    result: list[dict[str, object]] = []
    if kind is HotspotKind.FILES:
        for file_entry in hotspots.get("topFiles", []):
            record: dict[str, object] = {
                "path": file_entry.get("path", "<unknown>"),
                "errors": coerce_int(file_entry.get("errors")),
                "warnings": coerce_int(file_entry.get("warnings")),
            }
            result.append(record)
    else:
        for folder_entry in hotspots.get("topFolders", []):
            folder_record: dict[str, object] = {
                "path": folder_entry.get("path", "<unknown>"),
                "errors": coerce_int(folder_entry.get("errors")),
                "warnings": coerce_int(folder_entry.get("warnings")),
                "information": coerce_int(folder_entry.get("information")),
                "participating_runs": coerce_int(folder_entry.get("participatingRuns")),
            }
            code_counts_map = coerce_mapping(folder_entry.get("codeCounts"))
            if code_counts_map:
                folder_record["code_counts"] = code_counts_map
            recommendations_list = coerce_object_list(folder_entry.get("recommendations"))
            if recommendations_list:
                folder_record["recommendations"] = [str(item) for item in recommendations_list]
            result.append(folder_record)
    if limit > 0:
        return result[:limit]
    return result


def query_readiness(
    summary: SummaryData,
    *,
    level: ReadinessLevel,
    statuses: Sequence[ReadinessStatus] | None,
    limit: int,
) -> dict[str, list[dict[str, object]]]:
    """Build the payload for ``typewiz query readiness``."""
    return collect_readiness_view(summary, level=level, statuses=statuses, limit=limit)


def query_runs(
    summary: SummaryData,
    *,
    tools: Sequence[str] | None,
    modes: Sequence[str] | None,
    limit: int,
) -> list[dict[str, object]]:
    """Build the payload for ``typewiz query runs``."""
    runs = summary["tabs"]["runs"]["runSummary"]
    tool_filter = {tool for tool in tools or [] if tool}
    mode_filter = {mode for mode in modes or [] if mode}
    records: list[dict[str, object]] = []
    for name, entry in sorted(runs.items()):
        parts = name.split(":", 1)
        tool = parts[0]
        mode = parts[1] if len(parts) == 2 else ""
        if tool_filter and tool not in tool_filter:
            continue
        if mode_filter and mode not in mode_filter:
            continue
        records.append(
            {
                "run": name,
                "tool": tool,
                "mode": mode,
                "errors": coerce_int(entry.get("errors")),
                "warnings": coerce_int(entry.get("warnings")),
                "information": coerce_int(entry.get("information")),
                "command": " ".join(entry.get("command", [])),
            },
        )
        if limit > 0 and len(records) >= limit:
            break
    return records


def query_engines(summary: SummaryData, *, limit: int) -> list[dict[str, object]]:
    """Build the payload for ``typewiz query engines``."""
    runs = summary["tabs"]["engines"]["runSummary"]
    records: list[dict[str, object]] = []
    for name, entry in sorted(runs.items()):
        options = entry.get("engineOptions", {})
        records.append(
            {
                "run": name,
                "profile": options.get("profile"),
                "config_file": options.get("configFile"),
                "plugin_args": coerce_str_list(options.get("pluginArgs", [])),
                "include": coerce_str_list(options.get("include", [])),
                "exclude": coerce_str_list(options.get("exclude", [])),
                "overrides": coerce_object_list(options.get("overrides", [])),
            },
        )
        if limit > 0 and len(records) >= limit:
            break
    return records


def query_rules(summary: SummaryData, *, limit: int) -> list[dict[str, object]]:
    """Build the payload for ``typewiz query rules``."""
    rules = summary["tabs"]["hotspots"].get("topRules", {})
    entries = list(rules.items())
    if limit > 0:
        entries = entries[:limit]
    return [{"rule": rule, "count": int(count)} for rule, count in entries]


__all__ = [
    "SUMMARY_FIELD_CHOICES",
    "format_list",
    "parse_summary_fields",
    "print_readiness_summary",
    "print_summary",
    "query_engines",
    "query_hotspots",
    "query_overview",
    "query_readiness",
    "query_rules",
    "query_runs",
    "render_data",
]
