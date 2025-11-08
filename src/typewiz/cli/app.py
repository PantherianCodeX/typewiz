# Copyright (c) 2024 PantherianCodeX

"""CLI entry point and orchestration for typewiz commands."""

from __future__ import annotations

import argparse
import logging
import pathlib
from collections.abc import Callable, Sequence
from contextlib import suppress
from textwrap import dedent
from typing import Any, Final

from typewiz import __version__ as TYPEWIZ_VERSION
from typewiz.cli.commands import audit as audit_command
from typewiz.cli.commands import cache as cache_command
from typewiz.cli.commands import engines as engines_command
from typewiz.cli.commands import help as help_command
from typewiz.cli.commands import manifest as manifest_command
from typewiz.cli.commands import query as query_command
from typewiz.cli.commands import ratchet as ratchet_command
from typewiz.cli.helpers import SUMMARY_FIELD_CHOICES as _SUMMARY_FIELD_CHOICES
from typewiz.cli.helpers import echo as _echo
from typewiz.cli.helpers import print_readiness_summary as _helpers_print_readiness_summary
from typewiz.cli.helpers import register_argument as _register_argument
from typewiz.core.model_types import (
    DashboardFormat,
    DashboardView,
    LogFormat,
    ReadinessLevel,
    ReadinessStatus,
    SeverityLevel,
)
from typewiz.core.summary_types import SummaryData
from typewiz.license import maybe_emit_evaluation_notice
from typewiz.logging import LOG_FORMATS, configure_logging
from typewiz.runtime import consume
from typewiz.services.dashboard import (
    load_summary_from_manifest,
    render_dashboard_summary,
)

SUMMARY_FIELD_CHOICES = _SUMMARY_FIELD_CHOICES
logger: logging.Logger = logging.getLogger("typewiz.cli")


"""CLI helpers and command definitions for Typewiz."""


CONFIG_TEMPLATE: Final[str] = dedent(
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
    #   exclude = ["tests"]
    #
    # Files named typewiz.dir.toml or .typewizdir.toml are discovered recursively.
    """,
)


def write_config_template(path: pathlib.Path, *, force: bool) -> int:
    if path.exists() and not force:
        _echo(f"[typewiz] Refusing to overwrite existing file: {path}")
        _echo("Use --force if you want to replace it.")
        return 1
    path.parent.mkdir(parents=True, exist_ok=True)
    consume(path.write_text(CONFIG_TEMPLATE, encoding="utf-8"))
    _echo(f"[typewiz] Wrote starter config to {path}")
    return 0


CommandHandler = Callable[[argparse.Namespace], int]


def main(argv: Sequence[str] | None = None) -> int:
    maybe_emit_evaluation_notice(lambda message: _echo(message, err=True))
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.version:
        _echo(f"typewiz {TYPEWIZ_VERSION}")
        return 0
    if args.command is None:
        parser.error("No command provided.")
    _initialize_logging(args.log_format)
    handler = _command_handlers().get(args.command)
    if handler is None:
        parser.error(f"Unknown command {args.command}")
    return handler(args)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="typewiz",
        description="Collect typing diagnostics and readiness insights for Python projects.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    _register_argument(
        parser,
        "--log-format",
        choices=LOG_FORMATS,
        default="text",
        help="Select logging output format (human-readable text or structured JSON).",
    )
    _register_argument(
        parser,
        "--version",
        action="store_true",
        help="Print the typewiz version and exit.",
    )
    subparsers = parser.add_subparsers(dest="command")

    audit_command.register_audit_command(subparsers)
    manifest_command.register_manifest_command(subparsers)
    query_command.register_query_command(subparsers)
    ratchet_command.register_ratchet_command(subparsers)
    help_command.register_help_command(subparsers)
    cache_command.register_cache_command(subparsers)
    engines_command.register_engines_command(subparsers)

    _register_dashboard_command(subparsers)
    _register_init_command(subparsers)
    _register_readiness_command(subparsers)
    return parser


def _register_dashboard_command(subparsers: Any) -> None:
    dashboard = subparsers.add_parser(
        "dashboard",
        help="Render a summary from an existing manifest",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    _register_argument(
        dashboard,
        "--manifest",
        type=pathlib.Path,
        required=True,
        help="Path to a typing audit manifest.",
    )
    _register_argument(
        dashboard,
        "--format",
        choices=[fmt.value for fmt in DashboardFormat],
        default=DashboardFormat.JSON.value,
        help="Output format.",
    )
    _register_argument(
        dashboard,
        "--output",
        type=pathlib.Path,
        default=None,
        help="Optional output file.",
    )
    _register_argument(
        dashboard,
        "--view",
        choices=[view.value for view in DashboardView],
        default="overview",
        help="Default tab when generating HTML.",
    )


def _register_init_command(subparsers: Any) -> None:
    init = subparsers.add_parser(
        "init",
        help="Generate a starter configuration file",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    _register_argument(
        init,
        "-o",
        "--output",
        type=pathlib.Path,
        default=pathlib.Path("typewiz.toml"),
        help="Destination for the generated configuration file.",
    )
    _register_argument(
        init,
        "--force",
        action="store_true",
        help="Overwrite the output file if it already exists.",
    )


def _register_readiness_command(subparsers: Any) -> None:
    readiness = subparsers.add_parser(
        "readiness",
        help="Show top-N candidates for strict typing",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    _register_argument(
        readiness,
        "--manifest",
        type=pathlib.Path,
        required=True,
        help="Path to a typing audit manifest.",
    )
    _register_argument(
        readiness,
        "--level",
        choices=[level.value for level in ReadinessLevel],
        default=ReadinessLevel.FOLDER.value,
    )
    _register_argument(
        readiness,
        "--status",
        dest="statuses",
        action="append",
        choices=[status.value for status in ReadinessStatus],
        default=None,
        help="Status buckets to render (repeatable).",
    )
    _register_argument(readiness, "--limit", type=int, default=10)
    _register_argument(
        readiness,
        "--severity",
        dest="severities",
        action="append",
        choices=[severity.value for severity in SeverityLevel],
        default=None,
        help="Filter entries to specific severities (repeatable).",
    )
    _register_argument(
        readiness,
        "--details",
        action="store_true",
        help="Include severity breakdown when printing readiness summaries.",
    )


def _initialize_logging(log_format: str) -> None:
    with suppress(Exception):  # best-effort logger init
        configure_logging(LogFormat.from_str(log_format))


def _command_handlers() -> dict[str, CommandHandler]:
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


def _execute_init(args: argparse.Namespace) -> int:
    return write_config_template(args.output, force=args.force)


def _execute_dashboard(args: argparse.Namespace) -> int:
    summary = load_summary_from_manifest(args.manifest)
    dashboard_format = DashboardFormat.from_str(args.format)
    view_choice = DashboardView.from_str(args.view)
    rendered = render_dashboard_summary(
        summary,
        format=dashboard_format,
        default_view=view_choice,
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        consume(args.output.write_text(rendered, encoding="utf-8"))
    elif dashboard_format is DashboardFormat.JSON:
        _echo(rendered, newline=False)
    else:
        _echo(rendered)
    return 0


def _execute_readiness(args: argparse.Namespace) -> int:
    summary_map: SummaryData = load_summary_from_manifest(args.manifest)
    level_choice = ReadinessLevel.from_str(args.level)
    statuses = (
        [ReadinessStatus.from_str(status) for status in args.statuses] if args.statuses else None
    )
    severities = (
        [SeverityLevel.from_str(value) for value in args.severities]
        if getattr(args, "severities", None)
        else None
    )
    _helpers_print_readiness_summary(
        summary_map,
        level=level_choice,
        statuses=statuses,
        limit=args.limit,
        severities=severities,
        detailed=bool(getattr(args, "details", False)),
    )
    return 0
