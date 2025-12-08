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

"""Formatting and presentation helpers for the ratchetr CLI."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Literal, TypeAlias, cast

from ratchetr.common.override_utils import format_override_inline, override_detail_lines
from ratchetr.compat.python import TypedDict
from ratchetr.config.validation import (
    coerce_int,
    coerce_mapping,
    coerce_object_list,
    coerce_str_list,
)
from ratchetr.core.model_types import (
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
from ratchetr.core.type_aliases import RelPath, RunId
from ratchetr.error_codes import error_code_for
from ratchetr.json import JSONValue, normalise_enums_for_json
from ratchetr.readiness.views import ReadinessValidationError, ReadinessViewResult
from ratchetr.services.readiness import (
    collect_readiness_view as service_collect_readiness_view,
)
from ratchetr.services.readiness import (
    format_readiness_summary,
)

from .io import echo

if TYPE_CHECKING:
    from ratchetr.core.summary_types import (
        HotspotsTab,
        SummaryData,
        SummaryFileEntry,
        SummaryFolderEntry,
    )
    from ratchetr.core.types import RunResult


def stringify(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, str | int | float):
        return str(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, Mapping):
        mapping = cast("Mapping[str, JSONValue]", value)
        items: list[str] = []
        for key, val in mapping.items():
            items.append(f"{key}: {stringify(val)}")
        return "{" + ", ".join(items) + "}"
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        sequence = cast("Sequence[JSONValue]", value)
        return "[" + ", ".join(stringify(item) for item in sequence) + "]"
    return str(value)


def render_table_rows(rows: Sequence[Mapping[str, JSONValue]]) -> list[str]:
    if not rows:
        return ["<empty>"]
    headers = sorted({key for row in rows for key in row})
    widths: dict[str, int] = {}
    for header in headers:
        max_len = max(len(header), *(len(stringify(row.get(header))) for row in rows))
        widths[header] = max_len
    header_line = " | ".join(header.ljust(widths[header]) for header in headers)
    separator = "-+-".join("-" * widths[header] for header in headers)
    lines = [header_line, separator]
    lines.extend(" | ".join(stringify(row.get(header)).ljust(widths[header]) for header in headers) for row in rows)
    return lines


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


ReadinessQueryPayload: TypeAlias = ReadinessViewResult


FormatInput = Literal["json", "table"] | DataFormat


def _normalise_format(fmt: FormatInput) -> Literal["json", "table"]:
    if isinstance(fmt, DataFormat):
        return fmt.value
    return fmt


def _parse_run_identifier(raw: str) -> tuple[RunId, str, str]:
    """Parse ``tool:mode`` identifiers into typed components.

    Args:
        raw: Run identifier in the manifest (``tool:mode``).

    Returns:
        Tuple of ``RunId``, tool name, and mode string.
    """
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
    """Parse ``--summary-fields`` input, validating against allowable field names.

    Args:
        raw: Comma-separated CLI input or ``None``.
        valid_fields: Subset of allowable fields (defaults to all choices).

    Returns:
        Ordered list of ``SummaryField`` values.

    Raises:
        SystemExit: If the input references an unknown field.
    """
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
            msg = f"Unknown summary field '{item}'. Valid values: {readable}"
            raise SystemExit(msg)
        if field not in fields:
            fields.append(field)
    return fields


def _format_run_header(run: RunResult) -> str:
    counts = run.severity_counts()
    summary = (
        f"errors={counts.get(SeverityLevel.ERROR, 0)} "
        f"warnings={counts.get(SeverityLevel.WARNING, 0)} "
        f"info={counts.get(SeverityLevel.INFORMATION, 0)}"
    )
    command = " ".join(run.command)
    return f"[ratchetr] {run.tool}:{run.mode} exit={run.exit_code} {summary} ({command})"


def _collect_run_details(
    run: RunResult,
    *,
    fields: set[SummaryField],
    expanded: bool,
) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    if SummaryField.PROFILE in fields:
        items.extend(_profile_details(run, expanded=expanded))
    if SummaryField.CONFIG in fields:
        items.extend(_config_details(run, expanded=expanded))
    if SummaryField.PLUGIN_ARGS in fields:
        items.extend(_plugin_args_details(run, expanded=expanded))
    if SummaryField.PATHS in fields:
        items.extend(_paths_details(run, expanded=expanded))
    if SummaryField.OVERRIDES in fields:
        items.extend(_format_override_details(run.overrides, expanded=expanded))
    return items


def _format_override_details(
    overrides: Sequence[OverrideEntry],
    *,
    expanded: bool,
) -> list[tuple[str, str]]:
    cloned = clone_override_entries(overrides)
    if not cloned:
        return []
    if expanded:
        detailed: list[tuple[str, str]] = []
        for entry in cloned:
            path, details = override_detail_lines(entry)
            detailed.append((f"override {path}", "; ".join(details)))
        return detailed
    summary = [format_override_inline(entry) for entry in cloned]
    return [("overrides", "; ".join(summary))]


def _optional_detail(label: str, value: str | None, *, expanded: bool) -> list[tuple[str, str]]:
    if value or expanded:
        return [(label, value or "—")]
    return []


def _profile_details(run: RunResult, *, expanded: bool) -> list[tuple[str, str]]:
    return _optional_detail("profile", run.profile, expanded=expanded)


def _config_details(run: RunResult, *, expanded: bool) -> list[tuple[str, str]]:
    value = str(run.config_file) if run.config_file else None
    return _optional_detail("config", value, expanded=expanded)


def _plugin_args_details(run: RunResult, *, expanded: bool) -> list[tuple[str, str]]:
    plugin_args = format_list([str(arg) for arg in run.plugin_args])
    if plugin_args != "—" or expanded:
        return [("plugin args", plugin_args)]
    return []


def _paths_details(run: RunResult, *, expanded: bool) -> list[tuple[str, str]]:
    details: list[tuple[str, str]] = []
    include_paths = format_list([str(path) for path in run.include])
    exclude_paths = format_list([str(path) for path in run.exclude])
    if include_paths != "—" or expanded:
        details.append(("include", include_paths))
    if exclude_paths != "—" or expanded:
        details.append(("exclude", exclude_paths))
    return details


def _print_run_summary(
    run: RunResult,
    *,
    fields: set[SummaryField],
    style: SummaryStyle,
) -> None:
    header = _format_run_header(run)
    expanded = style is not SummaryStyle.COMPACT
    detail_items = _collect_run_details(run, fields=fields, expanded=expanded)
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
    """Collect readiness data with consistent error handling.

    Args:
        summary: Manifest summary payload.
        level: Granularity for readiness reporting.
        statuses: Optional subset of ``ReadinessStatus`` entries to include.
        limit: Maximum number of entries to return (``0`` = unlimited).
        severities: Optional severity filters.

    Returns:
        Readiness payload in the structure expected by CLI consumers.

    Raises:
        SystemExit: If readiness data cannot be validated (wraps
            ``ReadinessValidationError``).
    """
    try:
        return service_collect_readiness_view(
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
    lines = format_readiness_summary(
        summary,
        level=level,
        statuses=statuses,
        limit=limit,
        severities=severities,
        detailed=detailed,
    )
    for line in lines:
        echo(line)


def render_data(data: object, fmt: FormatInput) -> list[str]:
    """Render Python data for CLI output.

    Args:
        data: Arbitrary data structure returned by query commands.
        fmt: Desired format (``json`` or ``table``) possibly derived from
            ``DataFormat`` enumerations.

    Returns:
        List of lines representing the formatted payload.
    """
    fmt_value = _normalise_format(fmt)
    if fmt_value == "json":
        return [json.dumps(normalise_enums_for_json(data), indent=2, ensure_ascii=False)]
    if isinstance(data, list):
        table_rows: list[Mapping[str, JSONValue]] = []
        for item in cast("Sequence[object]", data):
            if isinstance(item, Mapping):
                mapping_item = cast("Mapping[object, object]", item)
                table_rows.append(coerce_mapping(mapping_item))
        return render_table_rows(table_rows)
    if isinstance(data, Mapping):
        mapping_data = coerce_mapping(cast("Mapping[object, object]", data))
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
    """Build the payload for ``ratchetr query overview``.

    Args:
        summary: Manifest summary payload.
        include_categories: Whether to include category totals.
        include_runs: Whether to embed per-run severity totals.

    Returns:
        Structured overview payload suitable for JSON or table rendering.
    """
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
        payload["category_totals"] = {str(key): coerce_int(value) for key, value in category_totals_map.items()}
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
    """Build the payload for ``ratchetr query hotspots``.

    Args:
        summary: Manifest summary payload.
        kind: Whether to request file or folder hotspots.
        limit: Maximum number of entries to return (``0`` = unlimited).

    Returns:
        Top hotspots in the requested shape.
    """
    hotspots = summary["tabs"]["hotspots"]
    if kind is HotspotKind.FILES:
        return _build_file_hotspot_entries(hotspots, limit=limit)
    return _build_folder_hotspot_entries(hotspots, limit=limit)


def _build_file_hotspot_entries(
    hotspots: HotspotsTab,
    *,
    limit: int,
) -> list[FileHotspotEntry]:
    source: Sequence[SummaryFileEntry] = hotspots["topFiles"]
    entries: list[FileHotspotEntry] = [
        FileHotspotEntry(
            path=str(file_entry.get("path", "<unknown>")),
            errors=coerce_int(file_entry.get("errors")),
            warnings=coerce_int(file_entry.get("warnings")),
        )
        for file_entry in source
    ]
    return entries[:limit] if limit > 0 else entries


def _build_folder_hotspot_entries(
    hotspots: HotspotsTab,
    *,
    limit: int,
) -> list[FolderHotspotEntry]:
    folder_entries: list[FolderHotspotEntry] = []
    source: Sequence[SummaryFolderEntry] = hotspots["topFolders"]
    for folder_entry in source:
        folder_record: FolderHotspotEntry = {
            "path": str(folder_entry.get("path", "<unknown>")),
            "errors": coerce_int(folder_entry.get("errors")),
            "warnings": coerce_int(folder_entry.get("warnings")),
            "information": coerce_int(folder_entry.get("information")),
            "participating_runs": coerce_int(folder_entry.get("participatingRuns")),
        }
        code_counts_map = coerce_mapping(folder_entry.get("codeCounts"))
        if code_counts_map:
            folder_record["code_counts"] = {str(key): coerce_int(value) for key, value in code_counts_map.items()}
        recommendations_list = coerce_object_list(folder_entry.get("recommendations"))
        if recommendations_list:
            folder_record["recommendations"] = [str(item) for item in recommendations_list]
        folder_entries.append(folder_record)
        if limit > 0 and len(folder_entries) >= limit:
            break
    return folder_entries[:limit] if limit > 0 else folder_entries


def query_readiness(
    summary: SummaryData,
    *,
    level: ReadinessLevel,
    statuses: Sequence[ReadinessStatus] | None,
    limit: int,
    severities: Sequence[SeverityLevel] | None = None,
) -> ReadinessQueryPayload:
    """Build the payload for ``ratchetr query readiness``.

    Args:
        summary: Manifest summary payload.
        level: Readiness aggregation level.
        statuses: Optional readiness statuses to filter.
        limit: Maximum entries to include.
        severities: Optional severity filters.

    Returns:
        Readiness query payload derived from ``summary``.
    """
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
    """Build the payload for ``ratchetr query runs``.

    Args:
        summary: Manifest summary payload.
        tools: Optional filter of tool names.
        modes: Optional filter of run modes.
        limit: Maximum number of entries to return (``0`` = unlimited).

    Returns:
        Run summary entries filtered according to the provided options.
    """
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
    """Build the payload for ``ratchetr query engines``.

    Args:
        summary: Manifest summary payload.
        limit: Maximum number of entries to return (``0`` = unlimited).

    Returns:
        List of engine configuration summaries keyed by run identifier.
    """
    runs = summary["tabs"]["engines"]["runSummary"]
    records: list[EngineEntry] = []
    for name, entry in sorted(runs.items()):
        run_id, _, _ = _parse_run_identifier(name)
        options = entry.get("engineOptions", {})
        profile = options.get("profile")
        config_file = options.get("configFile")
        records.append(
            EngineEntry(
                run=run_id,
                profile=profile if isinstance(profile, str) else None,
                config_file=config_file if isinstance(config_file, str) else None,
                plugin_args=_coerce_strs(options.get("pluginArgs", [])),
                include=_coerce_strs(options.get("include", [])),
                exclude=_coerce_strs(options.get("exclude", [])),
                overrides=_parse_override_entries(options.get("overrides", [])),
            )
        )
        if limit > 0 and len(records) >= limit:
            break
    return records


def _coerce_strs(value: object) -> list[str]:
    return coerce_str_list(value)


def _parse_override_entries(raw_overrides: object) -> list[OverrideEntry]:
    overrides: list[OverrideEntry] = []
    for override in coerce_object_list(raw_overrides):
        entry = _parse_single_override(override)
        if entry:
            overrides.append(entry)
    return overrides


def _parse_single_override(candidate: object) -> OverrideEntry | None:
    if not isinstance(candidate, Mapping):
        return None
    override_map = coerce_mapping(cast("Mapping[object, object]", candidate))
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
    include_paths = _coerce_rel_path_list(override_map.get("include", []))
    if include_paths:
        typed_entry["include"] = include_paths
    exclude_paths = _coerce_rel_path_list(override_map.get("exclude", []))
    if exclude_paths:
        typed_entry["exclude"] = exclude_paths
    return typed_entry or None


def _coerce_rel_path_list(raw: object) -> list[RelPath]:
    return [RelPath(str(path)) for path in coerce_str_list(raw) if str(path).strip()]


def query_rules(
    summary: SummaryData,
    *,
    limit: int,
    include_paths: bool,
) -> list[RuleEntry]:
    """Build the payload for ``ratchetr query rules``.

    Args:
        summary: Manifest summary payload.
        limit: Maximum number of rule entries to include.
        include_paths: Whether to attach file-level contributions per rule.

    Returns:
        Rule entries describing counts and optional path contributions.
    """
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
