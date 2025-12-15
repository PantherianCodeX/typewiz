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

"""CLI entry point and orchestration for ratchetr commands."""

from __future__ import annotations

import argparse
import logging
import pathlib
from collections.abc import Callable, Sequence
from contextlib import suppress
from textwrap import dedent
from typing import TYPE_CHECKING, Final

from ratchetr import __version__
from ratchetr.cli.commands import audit as audit_command
from ratchetr.cli.commands import cache as cache_command
from ratchetr.cli.commands import engines as engines_command
from ratchetr.cli.commands import help as help_command
from ratchetr.cli.commands import manifest as manifest_command
from ratchetr.cli.commands import query as query_command
from ratchetr.cli.commands import ratchet as ratchet_command
from ratchetr.cli.helpers import SUMMARY_FIELD_CHOICES as _SUMMARY_FIELD_CHOICES
from ratchetr.cli.helpers import (
    CLIContext,
    build_cli_context,
    build_path_overrides,
    discover_manifest_or_exit,
    finalise_targets,
    infer_stdout_format_from_save_flag,
    parse_readiness_tokens,
    parse_save_flag,
    query_readiness,
    register_output_options,
    register_path_overrides,
    register_readiness_flag,
    register_save_flag,
    render_data,
)
from ratchetr.cli.helpers import echo as _echo
from ratchetr.cli.helpers import print_readiness_summary as _helpers_print_readiness_summary
from ratchetr.cli.helpers import register_argument as _register_argument
from ratchetr.cli.helpers.options import StdoutFormat
from ratchetr.core.model_types import (
    DashboardFormat,
    DashboardView,
    DataFormat,
    LogFormat,
)
from ratchetr.logging import LOG_FORMATS, LOG_LEVELS, configure_logging
from ratchetr.paths import OutputFormat, OutputTarget
from ratchetr.runtime import consume
from ratchetr.services.dashboard import (
    emit_dashboard_outputs,
    load_summary_from_manifest,
    render_dashboard_summary,
)

if TYPE_CHECKING:
    from ratchetr.cli.types import SubparserCollection
    from ratchetr.core.summary_types import SummaryData

SUMMARY_FIELD_CHOICES = _SUMMARY_FIELD_CHOICES
logger: logging.Logger = logging.getLogger("ratchetr.cli")

RATCHETR_VERSION: Final[str] = __version__


"""CLI helpers and command definitions for ratchetr."""


CONFIG_TEMPLATE: Final[str] = dedent(
    """\
    # ratchetr configuration template
    # Save this file as ratchetr.toml in the root of your project.
    config_version = 0

    [audit]
    # Uncomment and adjust to pin the directories scanned during target audits.
    # include_paths = ["src", "tests"]

    # Engines that run by default (pyright and mypy ship with ratchetr).
    runners = ["pyright", "mypy"]

    # Configure failure thresholds or output destinations as needed:
    # fail_on = "warnings"           # choices: never, warnings, errors
    # manifest_path = "ratchetr/manifest.json"
    # dashboard_json = "ratchetr/dashboard.json"
    # dashboard_markdown = "ratchetr/dashboard.md"
    # dashboard_html = "ratchetr/dashboard.html"

    # Select default profiles per engine here, or via `ratchetr audit --profile`.
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

    # To scope settings to a folder, create a ratchetr.dir.toml file in that
    # directory. Example contents:
    #
    #   [active_profiles]
    #   pyright = "strict"
    #
    #   [engines.pyright]
    #   plugin_args = ["--warnings"]
    #   include = ["."]
    #   exclude = ["tests"]
    #
    # Files named ratchetr.dir.toml or .ratchetrdir.toml are discovered recursively.
    """,
)


def write_config_template(path: pathlib.Path, *, force: bool) -> int:
    """Write the ratchetr configuration template to a file.

    Args:
        path: Target path where the configuration file will be written.
        force: If True, overwrite the file if it already exists. If False, refuse to overwrite.

    Returns:
        int: Exit code (0 for success, 1 for failure).
    """
    if path.exists() and not force:
        _echo(f"[ratchetr] Refusing to overwrite existing file: {path}")
        _echo("Use --force if you want to replace it.")
        return 1
    path.parent.mkdir(parents=True, exist_ok=True)
    consume(path.write_text(CONFIG_TEMPLATE, encoding="utf-8"))
    _echo(f"[ratchetr] Wrote starter config to {path}")
    return 0


CommandHandler = Callable[[argparse.Namespace, CLIContext], int]


def main(argv: Sequence[str] | None = None) -> int:
    """Main CLI entry point for the ratchetr command-line interface.

    Parses command-line arguments, configures logging, and dispatches to the appropriate
    command handler based on user input.

    Args:
        argv: Command-line arguments to parse. If None, uses sys.argv.

    Returns:
        int: Exit code from the executed command handler (0 for success, non-zero for failure).
    """
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.version:
        _echo(f"ratchetr {RATCHETR_VERSION}")
        return 0
    if args.command is None:
        parser.error("No command provided.")
    _initialize_logging(args.log_format, args.log_level)
    handler = _command_handlers().get(args.command)
    if handler is None:
        parser.error(f"Unknown command {args.command}")
    overrides = build_path_overrides(args)
    context = build_cli_context(overrides)
    return handler(args, context)


def _build_parser() -> argparse.ArgumentParser:
    """Build and configure the main argument parser for the ratchetr CLI.

    Creates the top-level argument parser with global options (log format, log level, version)
    and registers all subcommands including audit, manifest, query, ratchet, dashboard, etc.

    Returns:
        argparse.ArgumentParser: Fully configured argument parser ready to parse CLI arguments.
    """
    common = argparse.ArgumentParser(add_help=False)
    register_output_options(common)
    register_path_overrides(common)
    _register_argument(
        common,
        "--log-format",
        choices=LOG_FORMATS,
        default="text",
        help="Select logging output format (human-readable text or structured JSON).",
    )
    _register_argument(
        common,
        "--log-level",
        choices=LOG_LEVELS,
        default="info",
        help="Set verbosity of logged events.",
    )
    parser = argparse.ArgumentParser(
        prog="ratchetr",
        parents=[common],
        description="Collect typing diagnostics and readiness insights for Python projects. `rtr` is an alias.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    _register_argument(
        parser,
        "--version",
        action="store_true",
        help="Print the ratchetr version and exit.",
    )
    subparsers = parser.add_subparsers(dest="command")

    parents = [common]
    audit_command.register_audit_command(subparsers, parents=parents)
    manifest_command.register_manifest_command(subparsers, parents=parents)
    query_command.register_query_command(subparsers, parents=parents)
    ratchet_command.register_ratchet_command(subparsers, parents=parents)
    help_command.register_help_command(subparsers, parents=parents)
    cache_command.register_cache_command(subparsers, parents=parents)
    engines_command.register_engines_command(subparsers, parents=parents)

    _register_dashboard_command(subparsers, parents=parents)
    _register_init_command(subparsers, parents=parents)
    _register_readiness_command(subparsers, parents=parents)
    return parser


def _register_dashboard_command(
    subparsers: SubparserCollection,
    *,
    parents: Sequence[argparse.ArgumentParser] | None,
) -> None:
    """Register the 'dashboard' subcommand with the argument parser.

    Configures the dashboard command with arguments for manifest path, output format,
    output file, and default view selection for HTML output.

    Args:
        subparsers: Subparser registry where the dashboard command will be added.
        parents: Shared parent parsers carrying global flags.
    """
    dashboard = subparsers.add_parser(
        "dashboard",
        help="Render a summary from an existing manifest",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        parents=parents or [],
    )
    register_save_flag(
        dashboard,
        flag="--save-as",
        dest="output",
        short_flag="-s",
    )
    _register_argument(
        dashboard,
        "--view",
        choices=[view.value for view in DashboardView],
        default="overview",
        help="Default tab when generating HTML.",
    )
    _register_argument(
        dashboard,
        "--dry-run",
        action="store_true",
        help="Render dashboards but skip writing files (validation only).",
    )


def _register_init_command(
    subparsers: SubparserCollection,
    *,
    parents: Sequence[argparse.ArgumentParser] | None,
) -> None:
    """Register the 'init' subcommand with the argument parser.

    Configures the init command with arguments for output path and force overwrite option.
    This command generates a starter ratchetr.toml configuration file.

    Args:
        subparsers: Subparser registry where the init command will be added.
        parents: Shared parent parsers carrying global flags.
    """
    init = subparsers.add_parser(
        "init",
        help="Generate a starter configuration file",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        parents=parents or [],
    )
    _register_argument(
        init,
        "-s",
        "--save-as",
        dest="output",
        type=pathlib.Path,
        default=pathlib.Path("ratchetr.toml"),
        help="Destination for the generated configuration file.",
    )
    _register_argument(
        init,
        "--force",
        action="store_true",
        help="Overwrite the output file if it already exists.",
    )


def _register_readiness_command(
    subparsers: SubparserCollection,
    *,
    parents: Sequence[argparse.ArgumentParser] | None,
) -> None:
    """Register the 'readiness' subcommand with the argument parser.

    Configures the readiness command with arguments for manifest path, readiness level,
    status filters, severity filters, display limits, and detail options. This command
    shows top-N candidates for strict typing based on audit results.

    Args:
        subparsers: Subparser registry where the readiness command will be added.
        parents: Shared parent parsers carrying global flags.
    """
    readiness = subparsers.add_parser(
        "readiness",
        help="Show top-N candidates for strict typing",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        parents=parents or [],
    )
    register_readiness_flag(readiness, default_enabled=True)


def _initialize_logging(log_format: str, log_level: str) -> None:
    """Initialize logging configuration for the CLI application.

    Attempts to configure logging with the specified format and level. Failures are
    silently suppressed (best-effort initialization).

    Args:
        log_format: Logging format string (e.g., "text" or "json").
        log_level: Logging level string (e.g., "info", "debug", "warning").
    """
    with suppress(Exception):  # best-effort logger init
        _ = configure_logging(LogFormat.from_str(log_format), log_level=log_level)


def _command_handlers() -> dict[str, CommandHandler]:
    """Return a mapping of command names to their handler functions.

    Returns:
        dict[str, CommandHandler]: Dictionary mapping command name strings to their
            corresponding handler functions.
    """
    return {
        "audit": audit_command.execute_audit,
        "cache": cache_command.execute_cache,
        "dashboard": _execute_dashboard,
        "engines": engines_command.execute_engines,
        "help": help_command.execute_help,
        "init": _execute_init,
        "manifest": manifest_command.execute_manifest,
        "query": query_command.execute_query,
        "ratchet": ratchet_command.execute_ratchet,
        "readiness": _execute_readiness,
    }


def _execute_init(args: argparse.Namespace, _: CLIContext) -> int:
    """Execute the 'init' command to generate a configuration file.

    Args:
        args: Parsed command-line arguments containing output path and force flag.

    Returns:
        int: Exit code (0 for success, 1 for failure).
    """
    return write_config_template(args.output, force=args.force)


def _execute_dashboard(args: argparse.Namespace, context: CLIContext) -> int:
    """Execute the 'dashboard' command to render a summary from a manifest.

    Loads summary data from the specified manifest file and renders it in the requested
    format (JSON, Markdown, or HTML). Output can be written to a file or printed to stdout.

    Args:
        args: Parsed command-line arguments containing manifest path, format, output path,
            view options, and dry-run flag.
        context: Shared CLI context containing resolved paths.

    Returns:
        int: Exit code (always 0 for success).

    Raises:
        SystemExit: If output format is unsupported.
    """
    manifest_path = discover_manifest_or_exit(context, cli_manifest=getattr(args, "manifest", None))
    summary = load_summary_from_manifest(manifest_path)
    view_choice = DashboardView.from_str(args.view)
    save_flag = parse_save_flag(
        getattr(args, "output", None),
        allowed_formats={OutputFormat.JSON, OutputFormat.MARKDOWN, OutputFormat.HTML},
    )
    default_target = OutputTarget(OutputFormat.HTML, path=context.resolved_paths.dashboard_path)
    targets = finalise_targets(save_flag, default_targets=(default_target,))
    base_stdout = StdoutFormat.from_str(getattr(args, "out", StdoutFormat.TEXT.value))
    stdout_format = infer_stdout_format_from_save_flag(args, base_stdout, save_flag=save_flag)
    stdout_dashboard_format = DashboardFormat.JSON if stdout_format is StdoutFormat.JSON else DashboardFormat.MARKDOWN
    rendered_stdout = render_dashboard_summary(
        summary,
        output_format=stdout_dashboard_format,
        default_view=view_choice,
    )
    if stdout_dashboard_format is DashboardFormat.JSON:
        _echo(rendered_stdout, newline=False)
    else:
        _echo(rendered_stdout)

    # Get dry-run flag
    dry_run = bool(getattr(args, "dry_run", False))

    # Use service layer for file writes
    for target in targets:
        output_path = _resolve_dashboard_target_path(target, context)
        if target.format is OutputFormat.JSON:
            emit_dashboard_outputs(
                summary,
                json_path=output_path,
                markdown_path=None,
                html_path=None,
                default_view=view_choice,
                dry_run=dry_run,
            )
        elif target.format is OutputFormat.MARKDOWN:
            emit_dashboard_outputs(
                summary,
                json_path=None,
                markdown_path=output_path,
                html_path=None,
                default_view=view_choice,
                dry_run=dry_run,
            )
        elif target.format is OutputFormat.HTML:
            emit_dashboard_outputs(
                summary,
                json_path=None,
                markdown_path=None,
                html_path=output_path,
                default_view=view_choice,
                dry_run=dry_run,
            )
        else:
            msg = f"Unsupported dashboard output format '{target.format.value}'"
            raise SystemExit(msg)

    return 0


def _resolve_dashboard_target_path(target: OutputTarget, context: CLIContext) -> pathlib.Path:
    if target.path is not None:
        return target.path
    tool_home = context.resolved_paths.tool_home
    if target.format is OutputFormat.JSON:
        return tool_home / "dashboard.json"
    if target.format is OutputFormat.MARKDOWN:
        return tool_home / "dashboard.md"
    return context.resolved_paths.dashboard_path


def _execute_readiness(args: argparse.Namespace, context: CLIContext) -> int:
    """Execute the 'readiness' command to show typing readiness candidates.

    Args:
        args: Parsed command-line arguments containing readiness tokens and output format.
        context: Shared CLI context providing manifest discovery and paths.

    Returns:
        int: Exit code (always 0 for success).
    """
    manifest_path = discover_manifest_or_exit(context, cli_manifest=getattr(args, "manifest", None))
    summary_map: SummaryData = load_summary_from_manifest(manifest_path)
    readiness_tokens = getattr(args, "readiness", None)
    readiness = parse_readiness_tokens(readiness_tokens, flag_present=True)
    stdout_format = StdoutFormat.from_str(getattr(args, "out", StdoutFormat.TEXT.value))
    statuses = list(readiness.statuses) if readiness.statuses else None
    severities = list(readiness.severities) if readiness.severities else None
    if stdout_format is StdoutFormat.JSON:
        payload = query_readiness(
            summary_map,
            level=readiness.level,
            statuses=statuses,
            limit=readiness.limit,
            severities=severities,
        )
        for line in render_data(payload, DataFormat.JSON):
            _echo(line)
        return 0
    _helpers_print_readiness_summary(
        summary_map,
        level=readiness.level,
        statuses=statuses,
        limit=readiness.limit,
        severities=severities,
        detailed=readiness.include_details,
    )
    return 0
