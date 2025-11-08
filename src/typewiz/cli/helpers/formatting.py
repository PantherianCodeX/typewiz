# Copyright (c) 2024 PantherianCodeX
"""Formatting and presentation helpers for the Typewiz CLI."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Literal, TypedDict, cast

from typewiz._internal.error_codes import error_code_for
from typewiz.core.model_types import (
    DataFormat,
    HotspotKind,
    OverrideEntry,
    ReadinessLevel,
    ReadinessStatus,
    SeverityLevel,
    SummaryField,
    SummaryStyle,
    clone_override_entries,
)
from typewiz.core.summary_types import SummaryData
from typewiz.core.type_aliases import RelPath, RunId
from typewiz.core.types import RunResult
from typewiz.data_validation import coerce_int, coerce_mapping, coerce_object_list, coerce_str_list
from typewiz.formatting import render_table_rows, stringify
from typewiz.override_utils import format_override_inline, override_detail_lines
from typewiz.readiness_views import (
    FileReadinessPayload,
    FolderReadinessPayload,
    ReadinessValidationError,
    ReadinessViewResult,
)
from typewiz.readiness_views import collect_readiness_view as _collect_readiness_view
from typewiz.utils import JSONValue, normalise_enums_for_json

from .io import echo

SUMMARY_FIELD_CHOICES: set[SummaryField] = set(SummaryField)


class OverviewRunEntry(TypedDict):
    run: str
    errors: int
    warnings: int
    information: int
    total: int


class OverviewQueryPayloadBase(TypedDict):
    generated_at: str | None
    project_root: str | None
    severity_totals: dict[str, int]


class OverviewQueryPayload(OverviewQueryPayloadBase, total=False):
    category_totals: dict[str, int]
    runs: list[OverviewRunEntry]


class FileHotspotEntry(TypedDict):
    path: str
    errors: int
    warnings: int


class FolderHotspotEntryBase(TypedDict):
    path: str
    errors: int
    warnings: int
    information: int
    participating_runs: int


class FolderHotspotEntry(FolderHotspotEntryBase, total=False):
    code_counts: dict[str, int]
    recommendations: list[str]


class RunSummaryEntry(TypedDict):
    run: str
    tool: str
    mode: str
    errors: int
    warnings: int
    information: int
    command: str


class EngineEntry(TypedDict):
    run: str
    profile: str | None
    config_file: str | None
    plugin_args: list[str]
    include: list[str]
    exclude: list[str]
    overrides: list[OverrideEntry]


class RuleEntryRequired(TypedDict):
    rule: str
    count: int


class RulePathEntry(TypedDict):
    path: str
    count: int


class RuleEntry(RuleEntryRequired, total=False):
    paths: list[RulePathEntry]


type ReadinessQueryPayload = ReadinessViewResult


FormatInput = Literal["json", "table"] | DataFormat


def _normalise_format(fmt: FormatInput) -> Literal["json", "table"]:
    if isinstance(fmt, DataFormat):
        return fmt.value
    return fmt


def _parse_run_identifier(raw: str) -> tuple[RunId, str, str]:
    """Parse ``tool:mode`` identifiers into typed components."""
    tool, sep, remainder = raw.partition(":")
    mode = remainder if sep else ""
    return RunId(raw), tool, mode


def format_list(values: Sequence[str]) -> str:
    """Return a comma-separated string for CLI presentation."""
    return ", ".join(values) if values else "—"


def parse_summary_fields(
    raw: str | None,
    *,
    valid_fields: set[SummaryField] | None = None,
) -> list[SummaryField]:
    """Parse ``--summary-fields`` input, validating against allowable field names."""
    field_set = valid_fields if valid_fields is not None else SUMMARY_FIELD_CHOICES
    if not raw:
        return []
    name_map = {field.value: field for field in field_set}
    fields: list[SummaryField] = []
    for part in raw.split(","):
        item = part.strip().lower()
        if not item:
            continue
        if item == "all":
            return sorted(field_set, key=lambda field: field.value)
        field = name_map.get(item)
        if field is None:
            readable = ", ".join(sorted({*name_map, "all"}))
            raise SystemExit(f"Unknown summary field '{item}'. Valid values: {readable}")
        if field not in fields:
            fields.append(field)
    return fields


def _print_run_summary(
    run: RunResult,
    *,
    fields: set[SummaryField],
    style: SummaryStyle,
) -> None:
    counts = run.severity_counts()
    summary = (
        f"errors={counts.get(SeverityLevel.ERROR, 0)} "
        f"warnings={counts.get(SeverityLevel.WARNING, 0)} "
        f"info={counts.get(SeverityLevel.INFORMATION, 0)}"
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
    severities: Sequence[SeverityLevel] | None = None,
) -> ReadinessQueryPayload:
    """Collect readiness data with consistent error handling."""
    try:
        return _collect_readiness_view(
            summary,
            level=level,
            statuses=statuses,
            limit=limit,
            severities=severities,
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
    severities: Sequence[SeverityLevel] | None = None,
    detailed: bool = False,
) -> None:
    """Print a readiness summary in the same shape as historic CLI output."""
    view = collect_readiness_view(
        summary,
        level=level,
        statuses=statuses,
        limit=limit,
        severities=severities,
    )

    def _format_counts(
        label: str,
        entry: FolderReadinessPayload | FileReadinessPayload,
    ) -> str:
        if not detailed:
            return label
        errors = entry.get("errors", 0)
        warnings = entry.get("warnings", 0)
        information = entry.get("information", 0)
        return f"{label} (errors={errors} warnings={warnings} info={information})"

    if level is ReadinessLevel.FOLDER:
        folder_view: dict[ReadinessStatus, list[FolderReadinessPayload]] = cast(
            dict[ReadinessStatus, list[FolderReadinessPayload]],
            view,
        )
        for status, folder_entries in folder_view.items():
            echo(f"[typewiz] readiness {level.value} status={status.value} (top {limit})")
            if not folder_entries:
                echo("  <none>")
                continue
            for folder_entry in folder_entries:
                label = f"  {folder_entry['path']}: {folder_entry['count']}"
                echo(_format_counts(label, folder_entry))
        return

    file_view: dict[ReadinessStatus, list[FileReadinessPayload]] = cast(
        dict[ReadinessStatus, list[FileReadinessPayload]],
        view,
    )
    for status, file_entries in file_view.items():
        echo(f"[typewiz] readiness {level.value} status={status.value} (top {limit})")
        if not file_entries:
            echo("  <none>")
            continue
        for file_entry in file_entries:
            label = f"  {file_entry['path']}: {file_entry['diagnostics']}"
            echo(_format_counts(label, file_entry))


def render_data(data: object, fmt: FormatInput) -> list[str]:
    """Render Python data for CLI output."""
    fmt_value = _normalise_format(fmt)
    if fmt_value == "json":
        return [json.dumps(normalise_enums_for_json(data), indent=2, ensure_ascii=False)]
    if isinstance(data, list):
        table_rows: list[Mapping[str, JSONValue]] = []
        for item in cast("Sequence[object]", data):
            if isinstance(item, Mapping):
                mapping_item = cast(Mapping[object, object], item)
                table_rows.append(coerce_mapping(mapping_item))
        return render_table_rows(table_rows)
    if isinstance(data, Mapping):
        mapping_data = coerce_mapping(cast(Mapping[object, object], data))
        dict_rows: list[Mapping[str, JSONValue]] = [
            {"key": str(key), "value": value} for key, value in mapping_data.items()
        ]
        return render_table_rows(dict_rows)
    return [stringify(data)]


def query_overview(
    summary: SummaryData,
    *,
    include_categories: bool,
    include_runs: bool,
) -> OverviewQueryPayload:
    """Build the payload for ``typewiz query overview``."""
    overview = summary["tabs"]["overview"]
    severity_totals_map = coerce_mapping(overview.get("severityTotals", {}))
    severity_totals = {str(key): coerce_int(value) for key, value in severity_totals_map.items()}
    payload: OverviewQueryPayload = {
        "generated_at": summary["generatedAt"],
        "project_root": summary["projectRoot"],
        "severity_totals": severity_totals,
    }
    if include_categories:
        category_totals_map = coerce_mapping(overview.get("categoryTotals", {}))
        payload["category_totals"] = {
            str(key): coerce_int(value) for key, value in category_totals_map.items()
        }
    if include_runs:
        runs: list[OverviewRunEntry] = []
        for name, entry in overview.get("runSummary", {}).items():
            errors = coerce_int(entry.get("errors"))
            warnings = coerce_int(entry.get("warnings"))
            information = coerce_int(entry.get("information"))
            total = coerce_int(entry.get("total")) or errors + warnings + information
            runs.append(
                OverviewRunEntry(
                    run=name,
                    errors=errors,
                    warnings=warnings,
                    information=information,
                    total=total,
                )
            )
        payload["runs"] = runs
    return payload


def query_hotspots(
    summary: SummaryData,
    *,
    kind: HotspotKind,
    limit: int,
) -> list[FileHotspotEntry] | list[FolderHotspotEntry]:
    """Build the payload for ``typewiz query hotspots``."""
    hotspots = summary["tabs"]["hotspots"]
    if kind is HotspotKind.FILES:
        result: list[FileHotspotEntry] = []
        for file_entry in hotspots.get("topFiles", []):
            result.append(
                FileHotspotEntry(
                    path=str(file_entry.get("path", "<unknown>")),
                    errors=coerce_int(file_entry.get("errors")),
                    warnings=coerce_int(file_entry.get("warnings")),
                )
            )
        if limit > 0:
            return result[:limit]
        return result

    folder_result: list[FolderHotspotEntry] = []
    for folder_entry in hotspots.get("topFolders", []):
        folder_record: FolderHotspotEntry = {
            "path": str(folder_entry.get("path", "<unknown>")),
            "errors": coerce_int(folder_entry.get("errors")),
            "warnings": coerce_int(folder_entry.get("warnings")),
            "information": coerce_int(folder_entry.get("information")),
            "participating_runs": coerce_int(folder_entry.get("participatingRuns")),
        }
        code_counts_map = coerce_mapping(folder_entry.get("codeCounts"))
        if code_counts_map:
            folder_record["code_counts"] = {
                str(key): coerce_int(value) for key, value in code_counts_map.items()
            }
        recommendations_list = coerce_object_list(folder_entry.get("recommendations"))
        if recommendations_list:
            folder_record["recommendations"] = [str(item) for item in recommendations_list]
        folder_result.append(folder_record)
    if limit > 0:
        return folder_result[:limit]
    return folder_result


def query_readiness(
    summary: SummaryData,
    *,
    level: ReadinessLevel,
    statuses: Sequence[ReadinessStatus] | None,
    limit: int,
    severities: Sequence[SeverityLevel] | None = None,
) -> ReadinessQueryPayload:
    """Build the payload for ``typewiz query readiness``."""
    return collect_readiness_view(
        summary,
        level=level,
        statuses=statuses,
        limit=limit,
        severities=severities,
    )


def query_runs(
    summary: SummaryData,
    *,
    tools: Sequence[str] | None,
    modes: Sequence[str] | None,
    limit: int,
) -> list[RunSummaryEntry]:
    """Build the payload for ``typewiz query runs``."""
    runs = summary["tabs"]["runs"]["runSummary"]
    tool_filter = {tool for tool in tools or [] if tool}
    mode_filter = {mode for mode in modes or [] if mode}
    records: list[RunSummaryEntry] = []
    for name, entry in sorted(runs.items()):
        run_id, tool, mode = _parse_run_identifier(name)
        if tool_filter and tool not in tool_filter:
            continue
        if mode_filter and mode not in mode_filter:
            continue
        records.append(
            RunSummaryEntry(
                run=run_id,
                tool=tool,
                mode=mode,
                errors=coerce_int(entry.get("errors")),
                warnings=coerce_int(entry.get("warnings")),
                information=coerce_int(entry.get("information")),
                command=" ".join(entry.get("command", [])),
            )
        )
        if limit > 0 and len(records) >= limit:
            break
    return records


def query_engines(summary: SummaryData, *, limit: int) -> list[EngineEntry]:
    """Build the payload for ``typewiz query engines``."""
    runs = summary["tabs"]["engines"]["runSummary"]
    records: list[EngineEntry] = []
    for name, entry in sorted(runs.items()):
        run_id, _, _ = _parse_run_identifier(name)
        options = entry.get("engineOptions", {})
        overrides_raw = coerce_object_list(options.get("overrides", []))
        overrides: list[OverrideEntry] = []
        for override in overrides_raw:
            if not isinstance(override, Mapping):
                continue
            override_map = coerce_mapping(cast(Mapping[object, object], override))
            typed_entry: OverrideEntry = {}
            path = override_map.get("path")
            if isinstance(path, str) and path:
                typed_entry["path"] = path
            profile = override_map.get("profile")
            if isinstance(profile, str) and profile:
                typed_entry["profile"] = profile
            plugin_args = coerce_str_list(override_map.get("pluginArgs", []))
            if plugin_args:
                typed_entry["pluginArgs"] = plugin_args
            include_paths = [
                RelPath(str(path))
                for path in coerce_str_list(override_map.get("include", []))
                if str(path).strip()
            ]
            if include_paths:
                typed_entry["include"] = include_paths
            exclude_paths = [
                RelPath(str(path))
                for path in coerce_str_list(override_map.get("exclude", []))
                if str(path).strip()
            ]
            if exclude_paths:
                typed_entry["exclude"] = exclude_paths
            if typed_entry:
                overrides.append(typed_entry)
        records.append(
            EngineEntry(
                run=run_id,
                profile=options.get("profile"),
                config_file=options.get("configFile"),
                plugin_args=coerce_str_list(options.get("pluginArgs", [])),
                include=coerce_str_list(options.get("include", [])),
                exclude=coerce_str_list(options.get("exclude", [])),
                overrides=overrides,
            )
        )
        if limit > 0 and len(records) >= limit:
            break
    return records


def query_rules(
    summary: SummaryData,
    *,
    limit: int,
    include_paths: bool,
) -> list[RuleEntry]:
    """Build the payload for ``typewiz query rules``."""
    hotspots = summary["tabs"]["hotspots"]
    rules = hotspots.get("topRules", {})
    rule_paths = hotspots.get("ruleFiles", {}) if include_paths else {}
    entries = list(rules.items())
    if limit > 0:
        entries = entries[:limit]
    result: list[RuleEntry] = []
    for rule, count in entries:
        entry: RuleEntry = RuleEntry(rule=rule, count=int(count))
        if include_paths:
            path_entries = [
                RulePathEntry(path=str(path_entry["path"]), count=int(path_entry["count"]))
                for path_entry in rule_paths.get(rule, [])
            ]
            if path_entries:
                entry["paths"] = path_entries
        result.append(entry)
    return result


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
