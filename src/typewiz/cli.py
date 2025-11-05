from __future__ import annotations

import argparse
import importlib
import json
import logging
import pathlib
import shlex
from collections.abc import Mapping
from textwrap import dedent
from typing import TYPE_CHECKING, Any, Literal, cast

from .api import run_audit
from .cli_helpers import collect_plugin_args as helpers_collect_plugin_args
from .cli_helpers import collect_profile_args as helpers_collect_profile_args
from .cli_helpers import format_list, render_data_structure
from .cli_helpers import normalise_modes as helpers_normalise_modes
from .cli_helpers import parse_summary_fields as helpers_parse_summary_fields
from .config import AuditConfig, load_config
from .dashboard import build_summary, load_manifest, render_markdown
from .data_validation import coerce_int, coerce_mapping, coerce_object_list, coerce_str_list
from .html_report import render_html
from .logging_utils import LOG_FORMATS, configure_logging
from .manifest_models import (
    ManifestValidationError,
    manifest_json_schema,
    validate_manifest_payload,
)
from .manifest_versioning import upgrade_manifest
from .model_types import clone_override_entries
from .override_utils import format_override_inline, override_detail_lines
from .readiness_views import ReadinessValidationError, collect_readiness_view
from .utils import default_full_paths, resolve_project_root

if TYPE_CHECKING:
    from collections.abc import Sequence
    from types import ModuleType

    from .summary_types import SummaryData
    from .types import RunResult

SUMMARY_FIELD_CHOICES = {"profile", "config", "plugin-args", "paths", "overrides"}
logger: logging.Logger = logging.getLogger("typewiz.cli")


"""CLI helpers and command definitions for Typewiz."""


CONFIG_TEMPLATE = dedent(
    """\
    # typewiz configuration template
    # Save this file as typewiz.toml in the root of your project.
    config_version = 0

    [audit]
    # Uncomment and adjust to pin the directories scanned during full audits.
    # full_paths = ["src", "tests"]

    # Engines that run by default (pyright and mypy ship with typewiz).
    runners = ["pyright", "mypy"]

    # Configure failure thresholds or output destinations as needed:
    # fail_on = "warnings"           # choices: never, warnings, errors
    # manifest_path = "typewiz/manifest.json"
    # dashboard_json = "typewiz/dashboard.json"
    # dashboard_markdown = "typewiz/dashboard.md"
    # dashboard_html = "typewiz/dashboard.html"

    # Select default profiles per engine here, or via `typewiz audit --profile`.
    [audit.active_profiles]
    # pyright = "baseline"
    # mypy = "strict"

    # Per-engine settings apply globally.
    [audit.engines.pyright]
    # plugin_args = ["--verifytypes"]
    # include = ["packages/api"]
    # exclude = ["packages/legacy"]
    # config_file = "configs/pyrightconfig.json"

    [audit.engines.pyright.profiles.strict]
    # inherit = "baseline"
    # plugin_args = ["--strict"]

    [audit.engines.mypy]
    # plugin_args = ["--strict"]
    # include = ["src"]
    # config_file = "configs/mypy.ini"

    # To scope settings to a folder, create a typewiz.dir.toml file in that
    # directory. Example contents:
    #
    #   [active_profiles]
    #   pyright = "strict"
    #
    #   [engines.pyright]
    #   plugin_args = ["--warnings"]
    #   include = ["."]
    #   exclude = ["legacy"]
    #
    # Files named typewiz.dir.toml or .typewizdir.toml are discovered recursively.
    """
)


def _format_list(values: Sequence[str]) -> str:
    return format_list(values)


def _parse_summary_fields(raw: str | None) -> list[str]:
    return helpers_parse_summary_fields(raw, valid_fields=SUMMARY_FIELD_CHOICES)


def _print_summary(
    runs: Sequence[RunResult],
    fields: Sequence[str],
    style: str,
) -> None:
    field_set = set(fields)

    for run in runs:
        counts = run.severity_counts()
        summary = (
            f"errors={counts.get('error', 0)} "
            f"warnings={counts.get('warning', 0)} "
            f"info={counts.get('information', 0)}"
        )
        cmd = " ".join(shlex.quote(arg) for arg in run.command)

        detail_items: list[tuple[str, str]] = []
        if "profile" in field_set:
            if run.profile:
                detail_items.append(("profile", run.profile))
            elif style == "expanded":
                detail_items.append(("profile", "—"))
        if "config" in field_set:
            if run.config_file:
                detail_items.append(("config", str(run.config_file)))
            elif style == "expanded":
                detail_items.append(("config", "—"))
        if "plugin-args" in field_set:
            plugin_args = _format_list(list(run.plugin_args))
            if plugin_args != "—" or style == "expanded":
                detail_items.append(("plugin args", plugin_args))
        if "paths" in field_set:
            include_paths = _format_list(list(run.include))
            exclude_paths = _format_list(list(run.exclude))
            if include_paths != "—" or style == "expanded":
                detail_items.append(("include", include_paths))
            if exclude_paths != "—" or style == "expanded":
                detail_items.append(("exclude", exclude_paths))
        overrides_data = clone_override_entries(run.overrides)
        if "overrides" in field_set and overrides_data:
            if style == "expanded":
                for entry in overrides_data:
                    path, details = override_detail_lines(entry)
                    detail_items.append((f"override {path}", "; ".join(details)))
            else:
                short = [format_override_inline(entry) for entry in overrides_data]
                detail_items.append(("overrides", "; ".join(short)))

        header = f"[typewiz] {run.tool}:{run.mode} exit={run.exit_code} {summary} ({cmd})"

        if style == "expanded" and detail_items:
            print(header)
            for label, value in detail_items:
                print(f"           - {label}: {value}")
        else:
            if detail_items:
                inline = " ".join(f"{label}={value}" for label, value in detail_items)
                print(f"{header} [{inline}]")
            else:
                print(header)


def _collect_readiness_view(
    summary: SummaryData,
    *,
    level: Literal["folder", "file"],
    statuses: Sequence[str] | None,
    limit: int,
) -> dict[str, list[dict[str, object]]]:
    try:
        return collect_readiness_view(summary, level=level, statuses=statuses, limit=limit)
    except ReadinessValidationError as exc:
        message = f"Invalid readiness data encountered: {exc}"
        raise SystemExit(message) from exc


def _print_readiness_summary(
    summary: SummaryData,
    *,
    level: str,
    statuses: Sequence[str] | None,
    limit: int,
) -> None:
    view = _collect_readiness_view(
        summary,
        level="folder" if level == "folder" else "file",
        statuses=statuses,
        limit=limit,
    )
    for status, entries in view.items():
        print(f"[typewiz] readiness {level} status={status} (top {limit})")
        if not entries:
            print("  <none>")
            continue
        for entry in entries:
            path = str(entry.get("path", "<unknown>"))
            count = entry.get("count") if level == "folder" else entry.get("diagnostics")
            count_int = coerce_int(count)
            print(f"  {path}: {count_int}")


def _render_data(data: object, fmt: Literal["json", "table"]) -> None:
    for line in render_data_structure(data, fmt):
        print(line)


def _query_overview(
    summary: SummaryData,
    *,
    include_categories: bool,
    include_runs: bool,
) -> dict[str, object]:
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
                }
            )
        payload["runs"] = runs
    return payload


def _query_hotspots(
    summary: SummaryData,
    *,
    kind: Literal["files", "folders"],
    limit: int,
) -> list[dict[str, object]]:
    hotspots = summary["tabs"]["hotspots"]
    result: list[dict[str, object]] = []
    if kind == "files":
        file_entries = hotspots.get("topFiles", [])
        for file_entry in file_entries:
            record: dict[str, object] = {
                "path": file_entry.get("path", "<unknown>"),
                "errors": coerce_int(file_entry.get("errors")),
                "warnings": coerce_int(file_entry.get("warnings")),
            }
            result.append(record)
    else:
        folder_entries = hotspots.get("topFolders", [])
        for folder_entry in folder_entries:
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


def _query_readiness(
    summary: SummaryData,
    *,
    level: Literal["folder", "file"],
    statuses: Sequence[str] | None,
    limit: int,
) -> dict[str, list[dict[str, object]]]:
    try:
        return _collect_readiness_view(summary, level=level, statuses=statuses, limit=limit)
    except ReadinessValidationError as exc:
        message = f"Invalid readiness data encountered: {exc}"
        raise SystemExit(message) from exc


def _query_runs(
    summary: SummaryData,
    *,
    tools: Sequence[str] | None,
    modes: Sequence[str] | None,
    limit: int,
) -> list[dict[str, object]]:
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
            }
        )
        if limit > 0 and len(records) >= limit:
            break
    return records


def _query_engines(
    summary: SummaryData,
    *,
    limit: int,
) -> list[dict[str, object]]:
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
            }
        )
        if limit > 0 and len(records) >= limit:
            break
    return records


def _query_rules(summary: SummaryData, *, limit: int) -> list[dict[str, object]]:
    rules = summary["tabs"]["hotspots"].get("topRules", {})
    entries = list(rules.items())
    if limit > 0:
        entries = entries[:limit]
    return [{"rule": rule, "count": int(count)} for rule, count in entries]


def _collect_plugin_args(entries: Sequence[str]) -> dict[str, list[str]]:
    return helpers_collect_plugin_args(entries)


def _collect_profile_args(pairs: Sequence[Sequence[str]]) -> dict[str, str]:
    flattened: list[str] = []
    for pair in pairs:
        if len(pair) != 2:
            message = "--profile entries must specify both runner and profile"
            raise SystemExit(message)
        runner_raw, profile_raw = pair[0], pair[1]
        runner = runner_raw.strip()
        profile = profile_raw.strip()
        if not runner or not profile:
            message = "--profile entries must specify both runner and profile"
            raise SystemExit(message)
        flattened.append(f"{runner}={profile}")
    return helpers_collect_profile_args(flattened)


def _normalise_modes(modes: Sequence[str] | None) -> tuple[bool, bool, bool]:
    normalised = helpers_normalise_modes(modes)
    if not normalised:
        return (False, True, True)
    run_current = "current" in normalised
    run_full = "full" in normalised
    if not run_current and not run_full:
        message = "No modes selected. Choose at least one of: current, full."
        raise SystemExit(message)
    return (True, run_current, run_full)


def _write_config_template(path: pathlib.Path, *, force: bool) -> int:
    if path.exists() and not force:
        print(f"[typewiz] Refusing to overwrite existing file: {path}")
        print("Use --force if you want to replace it.")
        return 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(CONFIG_TEMPLATE, encoding="utf-8")
    print(f"[typewiz] Wrote starter config to {path}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="typewiz",
        description="Collect typing diagnostics and readiness insights for Python projects.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--log-format",
        choices=LOG_FORMATS,
        default="text",
        help="Select logging output format (human-readable text or structured JSON).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    audit = subparsers.add_parser(
        "audit",
        help="Run typing audits and produce manifests/dashboards",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Collect diagnostics from configured engines and optionally write manifests or dashboards.",
    )
    audit.add_argument(
        "paths",
        nargs="*",
        metavar="PATH",
        help="Directories to include in full runs (default: auto-detected python packages).",
    )
    audit.add_argument(
        "-C",
        "--config",
        type=pathlib.Path,
        default=None,
        help="Path to a typewiz configuration file.",
    )
    audit.add_argument(
        "--project-root",
        type=pathlib.Path,
        default=None,
        help="Project root directory (defaults to the current working directory).",
    )
    audit.add_argument(
        "--manifest",
        type=pathlib.Path,
        default=None,
        help="Override the manifest output path.",
    )
    audit.add_argument(
        "-r",
        "--runner",
        dest="runners",
        action="append",
        metavar="NAME",
        default=None,
        help="Limit execution to the specified runner (repeatable).",
    )
    audit.add_argument(
        "-m",
        "--mode",
        dest="modes",
        action="append",
        choices=["current", "full"],
        help="Select which audit modes to run. Repeat to include multiple modes (default: both).",
    )
    audit.add_argument(
        "--max-depth",
        type=int,
        default=None,
        help="Folder aggregation depth for summaries.",
    )
    audit.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Maximum files to fingerprint for cache invalidation (protects giant repos).",
    )
    audit.add_argument(
        "--max-fingerprint-bytes",
        type=int,
        default=None,
        help="Upper bound on total bytes considered for fingerprinting (size budget).",
    )
    audit.add_argument(
        "--respect-gitignore",
        action="store_true",
        help="When fingerprinting, skip files ignored by .gitignore (requires git).",
    )
    audit.add_argument(
        "--plugin-arg",
        dest="plugin_arg",
        action="append",
        metavar="RUNNER=ARG",
        default=[],
        help="Pass an extra argument to a runner (repeatable). Example: --plugin-arg pyright=--verifytypes",
    )
    audit.add_argument(
        "--profile",
        dest="profiles",
        action="append",
        nargs=2,
        metavar=("RUNNER", "PROFILE"),
        default=[],
        help="Activate a named profile for a runner (repeatable).",
    )
    audit.add_argument(
        "-S",
        "--summary",
        choices=["compact", "expanded", "full"],
        default="compact",
        help="Compact (default), expanded (multi-line), or full (expanded + all fields).",
    )
    audit.add_argument(
        "--summary-fields",
        default=None,
        help="Comma-separated extra summary fields (profile, config, plugin-args, paths, all). Ignored for --summary=full.",
    )
    audit.add_argument(
        "--fail-on",
        choices=["none", "never", "warnings", "errors", "any"],
        default=None,
        help="Non-zero exit when diagnostics reach this severity (aliases: none=never, any=any finding).",
    )
    audit.add_argument(
        "--dashboard-json",
        type=pathlib.Path,
        default=None,
        help="Optional dashboard JSON output path.",
    )
    audit.add_argument(
        "--dashboard-markdown",
        type=pathlib.Path,
        default=None,
        help="Optional dashboard Markdown output path.",
    )
    audit.add_argument(
        "--dashboard-html",
        type=pathlib.Path,
        default=None,
        help="Optional dashboard HTML output path.",
    )
    audit.add_argument(
        "--compare-to",
        type=pathlib.Path,
        default=None,
        help="Optional path to a previous manifest to compare totals against (adds deltas to CI line).",
    )
    audit.add_argument(
        "--dashboard-view",
        choices=["overview", "engines", "hotspots", "runs"],
        default="overview",
        help="Default tab when writing the HTML dashboard.",
    )
    audit.add_argument(
        "--readiness",
        action="store_true",
        help="After audit completes, print a readiness summary.",
    )
    audit.add_argument(
        "--readiness-level",
        choices=["folder", "file"],
        default="folder",
        help="Granularity for readiness summaries when --readiness is enabled.",
    )
    audit.add_argument(
        "--readiness-status",
        dest="readiness_status",
        action="append",
        choices=["ready", "close", "blocked"],
        default=None,
        help="Status buckets to display for readiness summaries (repeatable).",
    )
    audit.add_argument(
        "--readiness-limit",
        type=int,
        default=10,
        help="Maximum entries per status when printing readiness summaries.",
    )

    dashboard = subparsers.add_parser(
        "dashboard",
        help="Render a summary from an existing manifest",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    dashboard.add_argument(
        "--manifest", type=pathlib.Path, required=True, help="Path to a typing audit manifest."
    )
    dashboard.add_argument(
        "--format",
        choices=["json", "markdown", "html"],
        default="json",
        help="Output format.",
    )
    dashboard.add_argument(
        "--output", type=pathlib.Path, default=None, help="Optional output file."
    )
    dashboard.add_argument(
        "--view",
        choices=["overview", "engines", "hotspots", "runs"],
        default="overview",
        help="Default tab when generating HTML.",
    )

    manifest_cmd = subparsers.add_parser(
        "manifest",
        help="Work with manifest files (validate)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    manifest_sub = manifest_cmd.add_subparsers(dest="action", required=True)
    manifest_validate = manifest_sub.add_parser(
        "validate",
        help="Validate a manifest against the JSON schema",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    manifest_validate.add_argument(
        "path", type=pathlib.Path, help="Path to manifest file to validate"
    )
    manifest_validate.add_argument(
        "--schema",
        type=pathlib.Path,
        default=None,
        help="Optionally validate against an additional JSON schema",
    )

    manifest_schema = manifest_sub.add_parser(
        "schema",
        help="Emit the manifest JSON schema",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    manifest_schema.add_argument(
        "--output",
        type=pathlib.Path,
        default=None,
        help="Write the schema to a path instead of stdout",
    )
    manifest_schema.add_argument(
        "--indent",
        type=int,
        default=2,
        help="Indentation level for JSON output",
    )

    manifest_migrate = manifest_sub.add_parser(
        "migrate",
        help="Rewrite a manifest to the current schema",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    manifest_migrate.add_argument(
        "--input",
        type=pathlib.Path,
        required=True,
        help="Manifest to migrate",
    )
    manifest_migrate.add_argument(
        "--output",
        type=pathlib.Path,
        default=None,
        help="Optional path to write migrated manifest (defaults to input path)",
    )

    query = subparsers.add_parser(
        "query",
        help="Inspect sections of a manifest summary without external tools",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    query_sub = query.add_subparsers(dest="query_section", required=True)

    query_overview = query_sub.add_parser(
        "overview",
        help="Show severity totals, with optional category and run breakdowns",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    query_overview.add_argument(
        "--manifest", type=pathlib.Path, required=True, help="Path to a typing audit manifest."
    )
    query_overview.add_argument(
        "--format",
        choices=["json", "table"],
        default="json",
        help="Output format",
    )
    query_overview.add_argument(
        "--include-categories",
        action="store_true",
        help="Include category totals in the response",
    )
    query_overview.add_argument(
        "--include-runs",
        action="store_true",
        help="Include per-run severity totals",
    )

    query_hotspots = query_sub.add_parser(
        "hotspots",
        help="List top offending files or folders",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    query_hotspots.add_argument(
        "--manifest", type=pathlib.Path, required=True, help="Path to a typing audit manifest."
    )
    query_hotspots.add_argument(
        "--kind",
        choices=["files", "folders"],
        default="files",
        help="Select hotspot view",
    )
    query_hotspots.add_argument("--limit", type=int, default=10, help="Maximum rows to return")
    query_hotspots.add_argument(
        "--format",
        choices=["json", "table"],
        default="json",
        help="Output format",
    )

    query_readiness = query_sub.add_parser(
        "readiness",
        help="Summarise readiness buckets (structured output)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    query_readiness.add_argument(
        "--manifest", type=pathlib.Path, required=True, help="Path to a typing audit manifest."
    )
    query_readiness.add_argument(
        "--level",
        choices=["folder", "file"],
        default="folder",
        help="Granularity for readiness data",
    )
    query_readiness.add_argument(
        "--status",
        dest="statuses",
        action="append",
        choices=["ready", "close", "blocked"],
        default=None,
        help="Filter specific readiness buckets (repeatable)",
    )
    query_readiness.add_argument("--limit", type=int, default=5, help="Maximum rows per status")
    query_readiness.add_argument(
        "--format",
        choices=["json", "table"],
        default="json",
        help="Output format",
    )

    query_runs = query_sub.add_parser(
        "runs",
        help="Inspect individual typing runs",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    query_runs.add_argument(
        "--manifest", type=pathlib.Path, required=True, help="Path to a typing audit manifest."
    )
    query_runs.add_argument(
        "--tool",
        dest="tools",
        action="append",
        default=None,
        help="Filter by tool name (repeatable, e.g., pyright)",
    )
    query_runs.add_argument(
        "--mode",
        dest="modes",
        action="append",
        default=None,
        help="Filter by mode (repeatable, e.g., current or full)",
    )
    query_runs.add_argument("--limit", type=int, default=10, help="Maximum runs to return")
    query_runs.add_argument(
        "--format",
        choices=["json", "table"],
        default="json",
        help="Output format",
    )

    query_engines = query_sub.add_parser(
        "engines",
        help="Display engine configuration used for runs",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    query_engines.add_argument(
        "--manifest", type=pathlib.Path, required=True, help="Path to a typing audit manifest."
    )
    query_engines.add_argument("--limit", type=int, default=10, help="Maximum rows to return")
    query_engines.add_argument(
        "--format",
        choices=["json", "table"],
        default="json",
        help="Output format",
    )

    query_rules = query_sub.add_parser(
        "rules",
        help="Show the most common rule diagnostics",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    query_rules.add_argument(
        "--manifest", type=pathlib.Path, required=True, help="Path to a typing audit manifest."
    )
    query_rules.add_argument("--limit", type=int, default=10, help="Maximum rules to return")
    query_rules.add_argument(
        "--format",
        choices=["json", "table"],
        default="json",
        help="Output format",
    )

    init = subparsers.add_parser(
        "init",
        help="Generate a starter configuration file",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    init.add_argument(
        "-o",
        "--output",
        type=pathlib.Path,
        default=pathlib.Path("typewiz.toml"),
        help="Destination for the generated configuration file.",
    )
    init.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the output file if it already exists.",
    )

    readiness = subparsers.add_parser(
        "readiness",
        help="Show top-N candidates for strict typing",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    readiness.add_argument(
        "--manifest", type=pathlib.Path, required=True, help="Path to a typing audit manifest."
    )
    readiness.add_argument("--level", choices=["folder", "file"], default="folder")
    readiness.add_argument(
        "--status",
        dest="statuses",
        action="append",
        choices=["ready", "close", "blocked"],
        default=None,
        help="Status buckets to render (repeatable).",
    )
    readiness.add_argument("--limit", type=int, default=10)

    args = parser.parse_args(list(argv) if argv is not None else None)
    from contextlib import suppress

    with suppress(Exception):  # best-effort logger init
        configure_logging(args.log_format)

    if args.command == "init":
        return _write_config_template(args.output, force=args.force)

    if args.command == "query":
        manifest = load_manifest(args.manifest)
        query_summary = build_summary(manifest)
        section = args.query_section
        data: object
        if section == "overview":
            data = _query_overview(
                query_summary,
                include_categories=args.include_categories,
                include_runs=args.include_runs,
            )
        elif section == "hotspots":
            data = _query_hotspots(
                query_summary,
                kind=args.kind,
                limit=args.limit,
            )
        elif section == "readiness":
            level_choice: Literal["folder", "file"] = "folder" if args.level == "folder" else "file"
            data = _query_readiness(
                query_summary,
                level=level_choice,
                statuses=args.statuses,
                limit=args.limit,
            )
        elif section == "runs":
            data = _query_runs(
                query_summary,
                tools=args.tools,
                modes=args.modes,
                limit=args.limit,
            )
        elif section == "engines":
            data = _query_engines(query_summary, limit=args.limit)
        elif section == "rules":
            data = _query_rules(query_summary, limit=args.limit)
        else:  # pragma: no cover - argparse restricts this path
            message = f"Unknown query section: {section}"
            raise SystemExit(message)
        _render_data(data, args.format)
        return 0

    if args.command == "audit":
        config = load_config(args.config)
        project_root = resolve_project_root(args.project_root)

        cli_full_paths = [path for path in args.paths if path]
        selected_full_paths = (
            cli_full_paths or config.audit.full_paths or default_full_paths(project_root)
        )
        if not selected_full_paths:
            message = "No paths found for full runs. Provide paths or configure 'full_paths'."
            raise SystemExit(message)

        modes_specified, run_current, run_full = _normalise_modes(args.modes)
        override = AuditConfig(
            manifest_path=args.manifest,
            full_paths=cli_full_paths or None,
            max_depth=args.max_depth,
            max_files=args.max_files,
            max_bytes=args.max_fingerprint_bytes,
            skip_current=(not run_current) if modes_specified else None,
            skip_full=(not run_full) if modes_specified else None,
            fail_on=args.fail_on,
            dashboard_json=args.dashboard_json,
            dashboard_markdown=args.dashboard_markdown,
            dashboard_html=args.dashboard_html,
            respect_gitignore=args.respect_gitignore,
            runners=args.runners,
        )
        if args.plugin_arg:
            plugin_arg_map = _collect_plugin_args(args.plugin_arg)
            for name, values in plugin_arg_map.items():
                override.plugin_args.setdefault(name, []).extend(values)
        if args.profiles:
            profile_entries: list[tuple[str, str]] = [
                (str(pair[0]), str(pair[1])) for pair in args.profiles
            ]
            override.active_profiles.update(_collect_profile_args(profile_entries))

        summary_choice: str = args.summary
        summary_style = "expanded" if summary_choice in {"expanded", "full"} else "compact"
        if summary_choice == "full":
            summary_fields = sorted(SUMMARY_FIELD_CHOICES)
        else:
            summary_fields = _parse_summary_fields(args.summary_fields)

        manifest_target = args.manifest if args.manifest else None
        result = run_audit(
            project_root=project_root,
            config=config,
            override=override,
            full_paths=selected_full_paths,
            write_manifest_to=manifest_target,
            build_summary_output=True,
        )

        _print_summary(result.runs, summary_fields, summary_style)

        audit_summary: SummaryData = result.summary or build_summary(result.manifest)

        if args.readiness:
            _print_readiness_summary(
                audit_summary,
                level=args.readiness_level,
                statuses=args.readiness_status,
                limit=args.readiness_limit,
            )

        fail_on = (args.fail_on or config.audit.fail_on or "never").lower()
        error_count = sum(run.severity_counts().get("error", 0) for run in result.runs)
        warning_count = sum(run.severity_counts().get("warning", 0) for run in result.runs)
        info_count = sum(run.severity_counts().get("information", 0) for run in result.runs)

        # Optional deltas against a previous manifest
        delta_str = ""
        if args.compare_to and args.compare_to.exists():
            try:
                from .dashboard import load_manifest as _load_manifest

                prev_manifest = _load_manifest(args.compare_to)
                prev_summary = build_summary(prev_manifest)
                prev_sev = prev_summary["tabs"]["overview"]["severityTotals"]
                de = error_count - int(prev_sev.get("error", 0))
                dw = warning_count - int(prev_sev.get("warning", 0))
                di = info_count - int(prev_sev.get("information", 0))

                def _fmt(x: int) -> str:
                    return f"+{x}" if x > 0 else (f"{x}" if x < 0 else "0")

                delta_str = f"; delta: errors={_fmt(de)} warnings={_fmt(dw)} info={_fmt(di)}"
            except Exception:
                delta_str = ""

        exit_code = 0
        if fail_on not in {"never", "none"} and (
            (fail_on == "errors" and error_count > 0)
            or (fail_on == "warnings" and (error_count > 0 or warning_count > 0))
            or (fail_on == "any" and (error_count > 0 or warning_count > 0 or info_count > 0))
        ):
            exit_code = 2

        # Compact CI summary line
        print(
            f"[typewiz] totals: errors={error_count} warnings={warning_count} info={info_count}; runs={len(result.runs)}"
            + delta_str
        )

        if args.dashboard_json:
            args.dashboard_json.parent.mkdir(parents=True, exist_ok=True)
            args.dashboard_json.write_text(
                json.dumps(audit_summary, indent=2) + "\n", encoding="utf-8"
            )
        if args.dashboard_markdown:
            args.dashboard_markdown.parent.mkdir(parents=True, exist_ok=True)
            args.dashboard_markdown.write_text(render_markdown(audit_summary), encoding="utf-8")
        if args.dashboard_html:
            args.dashboard_html.parent.mkdir(parents=True, exist_ok=True)
            args.dashboard_html.write_text(
                render_html(audit_summary, default_view=args.dashboard_view),
                encoding="utf-8",
            )

        return exit_code

    if args.command == "dashboard":
        manifest = load_manifest(args.manifest)
        summary = build_summary(manifest)
        if args.format == "json":
            rendered = json.dumps(summary, indent=2) + "\n"
        elif args.format == "markdown":
            rendered = render_markdown(summary)
        else:
            rendered = render_html(summary, default_view=args.view)

        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8")
        else:
            if args.format == "json":
                print(rendered, end="")
            else:
                print(rendered)

        return 0

    if args.command == "manifest":
        action = args.action
        if action == "validate":
            manifest_path: pathlib.Path = args.path
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))
            try:
                validate_manifest_payload(payload)
            except ManifestValidationError as exc:
                for err in exc.validation_error.errors():
                    location = ".".join(str(part) for part in err.get("loc", ())) or "<root>"
                    message = err.get("msg", "invalid value")
                    print(f"[typewiz] validation error at {location}: {message}")
                return 2

            schema_payload: dict[str, Any] | None
            if args.schema:
                schema_payload = json.loads(args.schema.read_text(encoding="utf-8"))
            else:
                schema_payload = manifest_json_schema()

            if schema_payload is not None:
                try:
                    jsonschema_module: ModuleType = importlib.import_module("jsonschema")
                except ModuleNotFoundError:
                    if args.schema:
                        print(
                            "[typewiz] jsonschema module not available; skipping schema validation"
                        )
                else:
                    validator = jsonschema_module.Draft7Validator(schema_payload)
                    errors = sorted(validator.iter_errors(payload), key=lambda e: e.path)
                    if errors:
                        for err in errors:
                            loc = "/".join(str(p) for p in err.path)
                            print(f"[typewiz] schema error at /{loc}: {err.message}")
                        return 2
            print("[typewiz] manifest is valid")
            return 0
        if action == "schema":
            schema: dict[str, Any] = manifest_json_schema()
            schema_text = json.dumps(schema, indent=args.indent)
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(schema_text + "\n", encoding="utf-8")
            else:
                print(schema_text)
            return 0
        if action == "migrate":
            input_path: pathlib.Path = args.input
            output_path = args.output or input_path
            payload = json.loads(input_path.read_text(encoding="utf-8"))
            if not isinstance(payload, Mapping):
                print("[typewiz] manifest migrate expects a JSON object payload")
                return 2
            upgraded = upgrade_manifest(cast(Mapping[str, object], payload))
            migrated = validate_manifest_payload(upgraded)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(migrated, indent=2) + "\n", encoding="utf-8")
            print(f"[typewiz] manifest migrated to {output_path}")
            return 0
        message = "Unknown manifest action"
        raise SystemExit(message)

    if args.command == "readiness":
        manifest = load_manifest(args.manifest)
        summary_map: SummaryData = build_summary(manifest)
        _print_readiness_summary(
            summary_map,
            level=args.level,
            statuses=args.statuses,
            limit=args.limit,
        )
        return 0

    message = f"Unknown command {args.command}"
    raise SystemExit(message)
