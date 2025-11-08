# Copyright (c) 2024 PantherianCodeX
"""Audit command wiring for the modular Typewiz CLI."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Protocol

from typewiz.api import build_summary
from typewiz.cli.helpers import (
    SUMMARY_FIELD_CHOICES,
    collect_plugin_args,
    collect_profile_args,
    normalise_modes,
    parse_hash_workers,
    parse_summary_fields,
    print_readiness_summary,
    print_summary,
    register_argument,
)
from typewiz.cli.helpers.io import echo as _echo
from typewiz.config import AuditConfig, Config, load_config
from typewiz.core.model_types import (
    DashboardView,
    FailOnPolicy,
    Mode,
    ReadinessLevel,
    ReadinessStatus,
    SeverityLevel,
    SummaryField,
    SummaryStyle,
)
from typewiz.core.summary_types import SummaryData
from typewiz.core.type_aliases import EngineName, ProfileName
from typewiz.runtime import default_full_paths, resolve_project_root
from typewiz.services.audit import run_audit
from typewiz.services.dashboard import emit_dashboard_outputs, load_summary_from_manifest


class SubparserRegistry(Protocol):
    def add_parser(
        self, *args: Any, **kwargs: Any
    ) -> argparse.ArgumentParser: ...  # pragma: no cover - Protocol


def register_audit_command(subparsers: SubparserRegistry) -> None:
    """Register the ``typewiz audit`` command and return the configured parser."""
    audit = subparsers.add_parser(
        "audit",
        help="Run typing audits and produce manifests/dashboards",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=(
            "Collect diagnostics from configured engines and optionally write manifests or dashboards."
        ),
    )

    register_argument(
        audit,
        "paths",
        nargs="*",
        metavar="PATH",
        help="Directories to include in full runs (default: auto-detected python packages).",
    )
    register_argument(
        audit,
        "-C",
        "--config",
        type=Path,
        default=None,
        help="Explicit typewiz.toml path (default: search in cwd).",
    )
    register_argument(
        audit,
        "--project-root",
        type=Path,
        default=None,
        help="Override the project root (default: auto-detected).",
    )
    register_argument(
        audit,
        "--manifest",
        type=Path,
        default=None,
        help="Write manifest JSON to this path.",
    )
    register_argument(
        audit,
        "--runner",
        dest="runners",
        action="append",
        default=None,
        help="Limit to specific engines (repeatable).",
    )
    register_argument(
        audit,
        "--mode",
        dest="modes",
        action="append",
        default=None,
        help="Select which modes to run (repeatable: current, full).",
    )
    register_argument(
        audit,
        "--max-depth",
        type=int,
        default=None,
        help="Limit directory recursion depth for fingerprinting.",
    )
    register_argument(
        audit,
        "--max-files",
        type=int,
        default=None,
        help="Limit number of files fingerprinted per run.",
    )
    register_argument(
        audit,
        "--max-fingerprint-bytes",
        type=int,
        default=None,
        help="Limit bytes fingerprinted per file.",
    )
    register_argument(
        audit,
        "--hash-workers",
        dest="hash_workers",
        default=None,
        metavar="WORKERS",
        help="Hash worker pool size ('auto' or non-negative integer).",
    )
    register_argument(
        audit,
        "--respect-gitignore",
        action="store_true",
        help="Respect .gitignore rules when expanding directories.",
    )
    register_argument(
        audit,
        "--plugin-arg",
        dest="plugin_arg",
        action="append",
        metavar="RUNNER=ARG",
        default=[],
        help="Pass an extra argument to a runner (repeatable). Example: --plugin-arg pyright=--verifytypes",
    )
    register_argument(
        audit,
        "--profile",
        dest="profiles",
        action="append",
        nargs=2,
        metavar=("RUNNER", "PROFILE"),
        default=[],
        help="Activate a named profile for a runner (repeatable).",
    )
    register_argument(
        audit,
        "-S",
        "--summary",
        choices=[style.value for style in SummaryStyle],
        default=SummaryStyle.COMPACT.value,
        help="Compact (default), expanded (multi-line), or full (expanded + all fields).",
    )
    register_argument(
        audit,
        "--summary-fields",
        default=None,
        help=(
            "Comma-separated extra summary fields (profile, config, plugin-args, paths, all). "
            "Ignored for --summary=full."
        ),
    )
    register_argument(
        audit,
        "--fail-on",
        choices=[policy.value for policy in FailOnPolicy],
        default=None,
        help="Non-zero exit when diagnostics reach this severity (aliases: none=never, any=any finding).",
    )
    register_argument(
        audit,
        "--dashboard-json",
        type=Path,
        default=None,
        help="Optional dashboard JSON output path.",
    )
    register_argument(
        audit,
        "--dashboard-markdown",
        type=Path,
        default=None,
        help="Optional dashboard Markdown output path.",
    )
    register_argument(
        audit,
        "--dashboard-html",
        type=Path,
        default=None,
        help="Optional dashboard HTML output path.",
    )
    register_argument(
        audit,
        "--compare-to",
        type=Path,
        default=None,
        help="Optional path to a previous manifest to compare totals against (adds deltas to CI line).",
    )
    register_argument(
        audit,
        "--dry-run",
        action="store_true",
        help="Skip writing manifests and dashboards; report summaries only.",
    )
    register_argument(
        audit,
        "--dashboard-view",
        choices=[view.value for view in DashboardView],
        default=DashboardView.OVERVIEW.value,
        help="Default tab when writing the HTML dashboard.",
    )
    register_argument(
        audit,
        "--readiness",
        action="store_true",
        help="After audit completes, print a readiness summary.",
    )
    register_argument(
        audit,
        "--readiness-level",
        choices=[level.value for level in ReadinessLevel],
        default=ReadinessLevel.FOLDER.value,
        help="Granularity for readiness summaries when --readiness is enabled.",
    )
    register_argument(
        audit,
        "--readiness-status",
        dest="readiness_status",
        action="append",
        choices=[status.value for status in ReadinessStatus],
        default=None,
        help="Status buckets to display for readiness summaries (repeatable).",
    )
    register_argument(
        audit,
        "--readiness-limit",
        type=int,
        default=10,
        help="Maximum entries per status when printing readiness summaries.",
    )
    register_argument(
        audit,
        "--readiness-severity",
        dest="readiness_severity",
        action="append",
        choices=[severity.value for severity in SeverityLevel],
        default=None,
        help="Filter readiness summaries to severities (repeatable).",
    )
    register_argument(
        audit,
        "--readiness-details",
        action="store_true",
        help="Include error/warning counts when printing readiness summaries.",
    )


def _resolve_full_paths(args: argparse.Namespace, config: Config, project_root: Path) -> list[str]:
    cli_full_paths = [path for path in args.paths if path]
    return cli_full_paths or config.audit.full_paths or default_full_paths(project_root)


def normalise_modes_tuple(modes: Sequence[str] | None) -> tuple[bool, bool, bool]:
    normalised = normalise_modes(modes)
    if not normalised:
        return (False, True, True)
    run_current = Mode.CURRENT in normalised
    run_full = Mode.FULL in normalised
    if not run_current and not run_full:
        raise SystemExit("No modes selected. Choose at least one of: current, full.")
    return (True, run_current, run_full)


def _update_override_with_plugin_args(override: AuditConfig, entries: Sequence[str]) -> None:
    plugin_arg_map = collect_plugin_args(entries)
    for name, values in plugin_arg_map.items():
        override.plugin_args.setdefault(EngineName(name), []).extend(values)


def _update_override_with_profiles(
    override: AuditConfig,
    entries: Sequence[Sequence[str]],
) -> None:
    flattened: list[str] = []
    for pair in entries:
        if len(pair) != 2:
            raise SystemExit("--profile entries must specify both runner and profile")
        runner, profile = pair
        runner_clean = runner.strip()
        profile_clean = profile.strip()
        if not runner_clean or not profile_clean:
            raise SystemExit("--profile entries must specify both runner and profile")
        flattened.append(f"{runner_clean}={profile_clean}")
    for runner, profile in collect_profile_args(flattened).items():
        override.active_profiles[EngineName(runner)] = ProfileName(profile)


def _resolve_summary_fields(args: argparse.Namespace) -> tuple[list[SummaryField], SummaryStyle]:
    style_choice = SummaryStyle.from_str(args.summary)
    if style_choice is SummaryStyle.FULL:
        return (sorted(SUMMARY_FIELD_CHOICES, key=lambda field: field.value), SummaryStyle.EXPANDED)
    render_style = (
        SummaryStyle.EXPANDED if style_choice is SummaryStyle.EXPANDED else SummaryStyle.COMPACT
    )
    return (
        parse_summary_fields(args.summary_fields, valid_fields=SUMMARY_FIELD_CHOICES),
        render_style,
    )


def _maybe_print_readiness(args: argparse.Namespace, summary: SummaryData) -> None:
    if not args.readiness:
        return
    level_choice = ReadinessLevel.from_str(args.readiness_level)
    statuses = (
        [ReadinessStatus.from_str(status) for status in args.readiness_status]
        if args.readiness_status
        else None
    )
    severities = (
        [SeverityLevel.from_str(value) for value in args.readiness_severity]
        if args.readiness_severity
        else None
    )
    print_readiness_summary(
        summary,
        level=level_choice,
        statuses=statuses,
        limit=args.readiness_limit,
        severities=severities,
        detailed=bool(getattr(args, "readiness_details", False)),
    )


def _build_delta_line(
    args: argparse.Namespace,
    error_count: int,
    warning_count: int,
    info_count: int,
) -> str:
    if not args.compare_to or not args.compare_to.exists():
        return ""
    try:
        prev_summary = load_summary_from_manifest(args.compare_to)
        prev_totals = prev_summary["tabs"]["overview"]["severityTotals"]
        de = error_count - int(prev_totals.get(SeverityLevel.ERROR, 0))
        dw = warning_count - int(prev_totals.get(SeverityLevel.WARNING, 0))
        di = info_count - int(prev_totals.get(SeverityLevel.INFORMATION, 0))

        def _fmt(value: int) -> str:
            return f"+{value}" if value > 0 else (f"{value}" if value < 0 else "0")

        return f"; delta: errors={_fmt(de)} warnings={_fmt(dw)} info={_fmt(di)}"
    except Exception:  # pragma: no cover - defensive guard mirrors historical behaviour
        return ""


def _emit_dashboard_outputs(args: argparse.Namespace, summary: SummaryData) -> None:
    view_choice = DashboardView.from_str(args.dashboard_view)
    emit_dashboard_outputs(
        summary,
        json_path=args.dashboard_json,
        markdown_path=args.dashboard_markdown,
        html_path=args.dashboard_html,
        default_view=view_choice,
    )


def execute_audit(args: argparse.Namespace) -> int:  # noqa: C901
    """Execute the ``typewiz audit`` command."""
    config = load_config(args.config)
    project_root = resolve_project_root(args.project_root)

    selected_full_paths = _resolve_full_paths(args, config, project_root)
    if not selected_full_paths:
        raise SystemExit("No paths found for full runs. Provide paths or configure 'full_paths'.")

    modes_specified, run_current, run_full = normalise_modes_tuple(args.modes)
    cli_fail_on = FailOnPolicy.from_str(args.fail_on) if args.fail_on else None
    override = AuditConfig(
        manifest_path=args.manifest,
        full_paths=[path for path in args.paths if path] or None,
        max_depth=args.max_depth,
        max_files=args.max_files,
        max_bytes=args.max_fingerprint_bytes,
        skip_current=(not run_current) if modes_specified else None,
        skip_full=(not run_full) if modes_specified else None,
        fail_on=cli_fail_on,
        hash_workers=parse_hash_workers(args.hash_workers),
        dashboard_json=args.dashboard_json,
        dashboard_markdown=args.dashboard_markdown,
        dashboard_html=args.dashboard_html,
        respect_gitignore=args.respect_gitignore,
        runners=args.runners,
    )

    if args.plugin_arg:
        _update_override_with_plugin_args(override, args.plugin_arg)
    if args.profiles:
        _update_override_with_profiles(override, args.profiles)

    dry_run = bool(args.dry_run)
    if dry_run:
        override.manifest_path = None
        override.dashboard_json = None
        override.dashboard_markdown = None
        override.dashboard_html = None
        if args.manifest or args.dashboard_json or args.dashboard_markdown or args.dashboard_html:
            _echo("[typewiz] --dry-run enabled; manifest and dashboard outputs are suppressed")

    summary_fields, summary_style = _resolve_summary_fields(args)

    manifest_target = None if dry_run else (args.manifest or None)

    result = run_audit(
        project_root=project_root,
        config=config,
        override=override,
        full_paths=selected_full_paths,
        write_manifest_to=manifest_target,
        build_summary_output=True,
        persist_outputs=not dry_run,
    )

    print_summary(result.runs, summary_fields, summary_style)

    audit_summary: SummaryData = result.summary or build_summary(result.manifest)

    _maybe_print_readiness(args, audit_summary)

    fail_on_policy = cli_fail_on or config.audit.fail_on or FailOnPolicy.NEVER
    if fail_on_policy is FailOnPolicy.NONE:
        fail_on_policy = FailOnPolicy.NEVER
    error_count = sum(run.severity_counts().get(SeverityLevel.ERROR, 0) for run in result.runs)
    warning_count = sum(run.severity_counts().get(SeverityLevel.WARNING, 0) for run in result.runs)
    info_count = sum(run.severity_counts().get(SeverityLevel.INFORMATION, 0) for run in result.runs)

    delta_segment = _build_delta_line(args, error_count, warning_count, info_count)

    exit_code = 0
    if fail_on_policy is FailOnPolicy.ERRORS and error_count > 0:
        exit_code = 2
    elif fail_on_policy is FailOnPolicy.WARNINGS and (error_count > 0 or warning_count > 0):
        exit_code = 2
    elif fail_on_policy is FailOnPolicy.ANY and (
        error_count > 0 or warning_count > 0 or info_count > 0
    ):
        exit_code = 2

    _echo(
        f"[typewiz] totals: errors={error_count} warnings={warning_count} info={info_count}; runs={len(result.runs)}"
        + delta_segment,
    )

    if not dry_run:
        _emit_dashboard_outputs(args, audit_summary)
    return exit_code


__all__ = ["execute_audit", "register_audit_command"]
