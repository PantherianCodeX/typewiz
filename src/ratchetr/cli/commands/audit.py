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

"""Audit command wiring for the modular ratchetr CLI."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from ratchetr.api import build_summary
from ratchetr.cli.helpers import (
    SUMMARY_FIELD_CHOICES,
    ReadinessOptions,
    SaveFlag,
    StdoutFormat,
    collect_plugin_args,
    collect_profile_args,
    finalise_targets,
    normalise_modes,
    parse_hash_workers,
    parse_readiness_tokens,
    parse_save_flag,
    parse_summary_fields,
    print_readiness_summary,
    print_summary,
    register_argument,
    register_readiness_flag,
    register_save_flag,
)
from ratchetr.cli.helpers.io import echo as _echo
from ratchetr.config import AuditConfig, Config
from ratchetr.core.model_types import (
    DashboardView,
    FailOnPolicy,
    Mode,
    SeverityLevel,
    SummaryField,
    SummaryStyle,
)
from ratchetr.core.type_aliases import EngineName, ProfileName
from ratchetr.json import normalise_enums_for_json
from ratchetr.paths import EnvOverrides, OutputFormat, OutputTarget
from ratchetr.services.audit import AuditResult, run_audit
from ratchetr.services.dashboard import emit_dashboard_outputs, load_summary_from_manifest
from ratchetr.services.manifest import emit_manifest_output

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ratchetr.cli.helpers import CLIContext
    from ratchetr.cli.types import SubparserCollection
    from ratchetr.core.summary_types import SummaryData
    from ratchetr.core.types import RunResult
    from ratchetr.manifest.typed import ManifestData


def register_audit_command(
    subparsers: SubparserCollection,
    *,
    parents: Sequence[argparse.ArgumentParser] | None = None,
) -> None:
    """Register the `ratchetr audit`command and return the configured parser.

    Args:
        subparsers: Top-level argparse subparser collection to register commands on.
        parents: Shared parent parsers carrying global options.
    """
    audit = subparsers.add_parser(
        "audit",
        help="Run typing audits and produce manifests/dashboards",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=("Collect diagnostics from configured engines and optionally write manifests or dashboards."),
        parents=parents or [],
    )

    register_argument(
        audit,
        "paths",
        nargs="*",
        metavar="PATH",
        help=(
            "Directories to include in audit scope (default: auto-detected python packages). Specify at end of command."
        ),
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
        help=("Pass an extra argument to a runner (repeatable). Example: --plugin-arg pyright=--verifytypes"),
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
        help=("Non-zero exit when diagnostics reach this severity (aliases: none=never, any=any finding)."),
    )
    register_save_flag(audit, flag="--save-as", dest="save_as", short_flag="-s")
    register_save_flag(audit, flag="--dashboard", dest="dashboard", short_flag="-d")
    # NOTE: --exclude flag roadmapped for future implementation (requires full
    # include/exclude scope resolution system)
    register_argument(
        audit,
        "--compare-to",
        type=Path,
        default=None,
        help=("Optional path to a previous manifest to compare totals against (adds deltas to CI line)."),
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
    register_readiness_flag(audit, default_enabled=False)


def _resolve_full_paths(
    args: argparse.Namespace,
    config: Config,
    env_overrides: EnvOverrides,
) -> list[str]:
    """Resolve audit scope paths using contract-defined precedence chain.

    Precedence (highest to lowest):
    1. CLI positional arguments
    2. Environment variable (RATCHETR_FULL_PATHS)
    3. Config file (audit.full_paths)
    4. Default: ["."] (scan everything from root)

    Args:
        args: Parsed CLI arguments.
        config: Loaded configuration.
        env_overrides: Environment variable overrides.

    Returns:
        List of paths to audit (relative to project root).
    """
    # 1. CLI positional arguments (highest priority)
    cli_paths = [path for path in args.paths if path]
    if cli_paths:
        return cli_paths

    # 2. Environment variable override
    if env_overrides.full_paths:
        return env_overrides.full_paths

    # 3. Config file setting
    if config.audit.full_paths:
        return config.audit.full_paths

    # 4. Default: scan everything from root (contract requirement)
    return ["."]


def normalise_modes_tuple(modes: Sequence[str] | None) -> tuple[bool, bool, bool]:
    """Normalise CLI mode selections into booleans for manifest handling.

    Args:
        modes: Optional sequence of raw mode strings from the CLI.

    Returns:
        Tuple of `(run_any, run_current, run_full)`flags indicating which audit modes to execute.

    Raises:
        SystemExit: If no modes are selected after normalisation.
    """
    normalised = normalise_modes(modes)
    if not normalised:
        return (False, True, True)
    run_current = Mode.CURRENT in normalised
    run_full = Mode.FULL in normalised
    if not run_current and not run_full:
        msg = "No modes selected. Choose at least one of: current, full."
        raise SystemExit(msg)
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
        # ignore JUSTIFIED: pairs must always contain exactly runner and profile tokens
        if len(pair) != 2:  # noqa: PLR2004
            msg = "--profile entries must specify both runner and profile"
            raise SystemExit(msg)
        runner, profile = pair
        runner_clean = runner.strip()
        profile_clean = profile.strip()
        if not runner_clean or not profile_clean:
            msg = "--profile entries must specify both runner and profile"
            raise SystemExit(msg)
        flattened.append(f"{runner_clean}={profile_clean}")
    for runner, profile in collect_profile_args(flattened).items():
        override.active_profiles[EngineName(runner)] = ProfileName(profile)


def _resolve_summary_fields(args: argparse.Namespace) -> tuple[list[SummaryField], SummaryStyle]:
    style_choice = SummaryStyle.from_str(args.summary)
    if style_choice is SummaryStyle.FULL:
        return (sorted(SUMMARY_FIELD_CHOICES, key=lambda field: field.value), SummaryStyle.EXPANDED)
    render_style = SummaryStyle.EXPANDED if style_choice is SummaryStyle.EXPANDED else SummaryStyle.COMPACT
    return (
        parse_summary_fields(args.summary_fields, valid_fields=SUMMARY_FIELD_CHOICES),
        render_style,
    )


def _maybe_print_readiness(readiness: ReadinessOptions, summary: SummaryData) -> None:
    if not readiness.enabled:
        return
    print_readiness_summary(
        summary,
        level=readiness.level,
        statuses=list(readiness.statuses) if readiness.statuses else None,
        limit=readiness.limit,
        severities=list(readiness.severities) if readiness.severities else None,
        detailed=readiness.include_details,
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
    except (OSError, KeyError, TypeError, ValueError):
        return ""


def _emit_dashboard_outputs(
    override: AuditConfig,
    dashboard_view: DashboardView,
    summary: SummaryData,
    *,
    dry_run: bool = False,
) -> None:
    """Emit dashboard outputs using the service layer.

    Args:
        override: Audit config with dashboard paths.
        dashboard_view: Default view for HTML.
        summary: Dashboard summary data.
        dry_run: If True, render but don't write files.
    """
    view_choice = dashboard_view
    emit_dashboard_outputs(
        summary,
        json_path=override.dashboard_json,
        markdown_path=override.dashboard_markdown,
        html_path=override.dashboard_html,
        default_view=view_choice,
        dry_run=dry_run,
    )


def _build_cli_override(
    args: argparse.Namespace,
    *,
    modes_specified: bool,
    run_current: bool,
    run_full: bool,
    cli_fail_on: FailOnPolicy | None,
    manifest_target: Path | None,
    dashboard_targets: tuple[OutputTarget, ...],
) -> AuditConfig:
    override = AuditConfig(
        manifest_path=manifest_target,
        full_paths=[path for path in args.paths if path] or None,
        max_depth=args.max_depth,
        max_files=args.max_files,
        max_bytes=args.max_fingerprint_bytes,
        skip_current=(not run_current) if modes_specified else None,
        skip_full=(not run_full) if modes_specified else None,
        fail_on=cli_fail_on,
        hash_workers=parse_hash_workers(args.hash_workers),
        respect_gitignore=args.respect_gitignore,
        runners=args.runners,
    )
    for target in dashboard_targets:
        if target.format is OutputFormat.JSON:
            override.dashboard_json = target.path
        elif target.format is OutputFormat.MARKDOWN:
            override.dashboard_markdown = target.path
        elif target.format is OutputFormat.HTML:
            override.dashboard_html = target.path
    if args.plugin_arg:
        _update_override_with_plugin_args(override, args.plugin_arg)
    if args.profiles:
        _update_override_with_profiles(override, args.profiles)
    return override


def _apply_dry_run_settings(
    args: argparse.Namespace,
    override: AuditConfig,
    manifest_target: Path | None,
    dashboard_targets: tuple[OutputTarget, ...],
) -> bool:
    dry_run = bool(args.dry_run)
    if not dry_run:
        return False
    override.manifest_path = None
    override.dashboard_json = None
    override.dashboard_markdown = None
    override.dashboard_html = None
    if manifest_target or dashboard_targets:
        _echo("[ratchetr] --dry-run enabled; manifest and dashboard outputs are suppressed")
    return True


def _resolve_manifest_target(save_flag: SaveFlag, context: CLIContext) -> Path | None:
    if save_flag.provided:
        targets = list(
            finalise_targets(
                save_flag,
                default_targets=(OutputTarget(OutputFormat.JSON, context.resolved_paths.manifest_path),),
            )
        )
        if not targets:
            msg = "audit requires at least one manifest target when --save-as is provided."
            raise SystemExit(msg)
        if len(targets) > 1:
            msg = "audit supports a single manifest target; specify one path."
            raise SystemExit(msg)
        target = targets[0]
        return target.path or context.resolved_paths.manifest_path
    if context.config.audit.manifest_path is not None:
        return context.config.audit.manifest_path
    return None


def _resolve_dashboard_targets(save_flag: SaveFlag, context: CLIContext) -> tuple[OutputTarget, ...]:
    if save_flag.provided:
        targets = finalise_targets(
            save_flag,
            default_targets=(OutputTarget(OutputFormat.HTML, context.resolved_paths.dashboard_path),),
        )
    else:
        cfg = context.config.audit
        targets = tuple(
            target
            for target in (
                OutputTarget(OutputFormat.JSON, cfg.dashboard_json) if cfg.dashboard_json else None,
                OutputTarget(OutputFormat.MARKDOWN, cfg.dashboard_markdown) if cfg.dashboard_markdown else None,
                OutputTarget(OutputFormat.HTML, cfg.dashboard_html) if cfg.dashboard_html else None,
            )
            if target is not None
        )
    resolved: list[OutputTarget] = []
    for target in targets:
        path = target.path or _default_dashboard_path(target.format, context)
        resolved.append(OutputTarget(target.format, path))
    return tuple(resolved)


def _default_dashboard_path(output_format: OutputFormat, context: CLIContext) -> Path:
    if output_format is OutputFormat.JSON:
        return context.resolved_paths.tool_home / "dashboard.json"
    if output_format is OutputFormat.MARKDOWN:
        return context.resolved_paths.tool_home / "dashboard.md"
    if output_format is OutputFormat.HTML:
        return context.resolved_paths.dashboard_path
    msg = f"Unsupported dashboard format '{output_format.value}'"
    raise SystemExit(msg)


@dataclass(slots=True)
# ignore JUSTIFIED: intentional - execution plan aggregates CLI/config inputs
class _AuditExecutionPlan:  # pylint: disable=too-many-instance-attributes
    config: Config
    project_root: Path
    full_paths: list[str]
    override: AuditConfig
    cli_fail_on: FailOnPolicy | None
    summary_fields: Sequence[SummaryField]
    summary_style: SummaryStyle
    dry_run: bool
    manifest_target: Path | None
    stdout_format: StdoutFormat
    readiness: ReadinessOptions
    dashboard_view: DashboardView


def _prepare_execution_plan(
    args: argparse.Namespace,
    *,
    context: CLIContext,
    manifest_target: Path | None,
    dashboard_targets: tuple[OutputTarget, ...],
    stdout_format: StdoutFormat,
    readiness: ReadinessOptions,
) -> _AuditExecutionPlan:
    config = context.config
    project_root = context.resolved_paths.repo_root
    selected_full_paths = _resolve_full_paths(args, config, context.env_overrides)
    if not selected_full_paths:
        msg = "No paths found for full runs. Provide paths or configure 'full_paths'."
        raise SystemExit(msg)

    modes_specified, run_current, run_full = normalise_modes_tuple(args.modes)
    cli_fail_on = FailOnPolicy.from_str(args.fail_on) if args.fail_on else None
    override = _build_cli_override(
        args,
        modes_specified=modes_specified,
        run_current=run_current,
        run_full=run_full,
        cli_fail_on=cli_fail_on,
        manifest_target=manifest_target,
        dashboard_targets=dashboard_targets,
    )

    dry_run = _apply_dry_run_settings(args, override, manifest_target, dashboard_targets)
    summary_fields, summary_style = _resolve_summary_fields(args)
    effective_manifest = None if dry_run else manifest_target

    return _AuditExecutionPlan(
        config=config,
        project_root=project_root,
        full_paths=selected_full_paths,
        override=override,
        cli_fail_on=cli_fail_on,
        summary_fields=summary_fields,
        summary_style=summary_style,
        dry_run=dry_run,
        manifest_target=effective_manifest,
        stdout_format=stdout_format,
        readiness=readiness,
        dashboard_view=DashboardView.from_str(args.dashboard_view),
    )


def _run_audit_plan(plan: _AuditExecutionPlan) -> AuditResult:
    return run_audit(
        project_root=plan.project_root,
        config=plan.config,
        override=plan.override,
        full_paths=plan.full_paths,
        build_summary_output=True,
    )


def _summarize_audit_run(
    args: argparse.Namespace,
    *,
    plan: _AuditExecutionPlan,
    result: AuditResult,
) -> tuple[SummaryData, int]:
    audit_summary: SummaryData = result.summary or build_summary(result.manifest)
    fail_on_policy = _resolve_fail_on_policy(plan.cli_fail_on, plan.config.audit.fail_on)
    error_count, warning_count, info_count = _accumulate_run_totals(result.runs)
    exit_code = _determine_exit_code(fail_on_policy, error_count, warning_count, info_count)

    if plan.stdout_format is StdoutFormat.JSON:
        _echo(json.dumps(normalise_enums_for_json(audit_summary), indent=2))
        return audit_summary, exit_code

    print_summary(result.runs, plan.summary_fields, plan.summary_style)
    _maybe_print_readiness(plan.readiness, audit_summary)

    delta_segment = _build_delta_line(args, error_count, warning_count, info_count)
    _echo(
        "[ratchetr] totals:"
        f" errors={error_count}"
        f" warnings={warning_count}"
        f" info={info_count}; runs={len(result.runs)}" + delta_segment,
    )
    return audit_summary, exit_code


def _persist_audit_outputs(
    *,
    plan: _AuditExecutionPlan,
    manifest: ManifestData,
    audit_summary: SummaryData,
) -> None:
    """Persist audit outputs (manifest and dashboards) via service layer.

    Args:
        plan: Audit execution plan with configuration and dry-run flag.
        manifest: Manifest data to persist.
        audit_summary: Summary data to persist.
    """
    # Write manifest if target is configured
    if plan.manifest_target:
        emit_manifest_output(
            manifest,
            manifest_path=plan.manifest_target,
            dry_run=plan.dry_run,
        )

    # Write dashboards
    _emit_dashboard_outputs(
        plan.override,
        plan.dashboard_view,
        audit_summary,
        dry_run=plan.dry_run,
    )


def _resolve_fail_on_policy(
    cli_fail_on: FailOnPolicy | None,
    config_fail_on: FailOnPolicy | None,
) -> FailOnPolicy:
    policy = cli_fail_on or config_fail_on or FailOnPolicy.NEVER
    if policy is FailOnPolicy.NONE:
        return FailOnPolicy.NEVER
    return policy


def _accumulate_run_totals(runs: Sequence[RunResult]) -> tuple[int, int, int]:
    error_count = sum(run.severity_counts().get(SeverityLevel.ERROR, 0) for run in runs)
    warning_count = sum(run.severity_counts().get(SeverityLevel.WARNING, 0) for run in runs)
    info_count = sum(run.severity_counts().get(SeverityLevel.INFORMATION, 0) for run in runs)
    return error_count, warning_count, info_count


def _determine_exit_code(
    policy: FailOnPolicy,
    error_count: int,
    warning_count: int,
    info_count: int,
) -> int:
    if policy is FailOnPolicy.ERRORS and error_count > 0:
        return 2
    if policy is FailOnPolicy.WARNINGS and (error_count > 0 or warning_count > 0):
        return 2
    if policy is FailOnPolicy.ANY and (error_count > 0 or warning_count > 0 or info_count > 0):
        return 2
    return 0


def execute_audit(args: argparse.Namespace, context: CLIContext) -> int:
    """Execute the `ratchetr audit`command.

    Args:
        args: Parsed CLI namespace produced by argparse.
        context: Shared CLI context containing configuration and resolved paths.

    Returns:
        Exit code honouring the configured `--fail-on`policy.
    """
    stdout_format = StdoutFormat.from_str(getattr(args, "out", StdoutFormat.TEXT.value))
    readiness_tokens = getattr(args, "readiness", None)
    readiness = parse_readiness_tokens(readiness_tokens, flag_present=readiness_tokens is not None)
    manifest_flag = parse_save_flag(getattr(args, "save_as", None), allowed_formats={OutputFormat.JSON})
    dashboard_flag = parse_save_flag(
        getattr(args, "dashboard", None),
        allowed_formats={OutputFormat.JSON, OutputFormat.MARKDOWN, OutputFormat.HTML},
    )
    manifest_target = _resolve_manifest_target(manifest_flag, context)
    dashboard_targets = _resolve_dashboard_targets(dashboard_flag, context)

    plan = _prepare_execution_plan(
        args,
        context=context,
        manifest_target=manifest_target,
        dashboard_targets=dashboard_targets,
        stdout_format=stdout_format,
        readiness=readiness,
    )
    result = _run_audit_plan(plan)
    audit_summary, exit_code = _summarize_audit_run(args, plan=plan, result=result)
    _persist_audit_outputs(plan=plan, manifest=result.manifest, audit_summary=audit_summary)
    return exit_code


__all__ = ["execute_audit", "register_audit_command"]
