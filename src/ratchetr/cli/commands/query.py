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

"""Query command implementation for the modular ratchetr CLI."""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING

from ratchetr.cli.helpers import (
    StdoutFormat,
    discover_manifest_or_exit,
    echo,
    parse_readiness_tokens,
    query_engines,
    query_hotspots,
    query_overview,
    query_readiness,
    query_rules,
    query_runs,
    register_argument,
    register_readiness_flag,
    render_data,
)
from ratchetr.core.model_types import (
    DataFormat,
    HotspotKind,
    QuerySection,
)
from ratchetr.services.dashboard import load_summary_from_manifest

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ratchetr.cli.helpers import CLIContext
    from ratchetr.cli.types import SubparserCollection


def register_query_command(
    subparsers: SubparserCollection,
    *,
    parents: Sequence[argparse.ArgumentParser] | None = None,
) -> None:
    """Register the `ratchetr query` command.

    Args:
        subparsers: Top-level argparse subparser collection to register commands on.
        parents: Shared parent parsers carrying global options.
    """
    query = subparsers.add_parser(
        "query",
        help="Inspect sections of a manifest summary without external tools",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        parents=parents or [],
    )
    query_sub = query.add_subparsers(dest="query_section", required=True)

    section_parents = list(parents or [])

    query_overview_parser = query_sub.add_parser(
        QuerySection.OVERVIEW.value,
        help="Show severity totals, with optional category and run breakdowns",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        parents=section_parents,
    )
    register_argument(
        query_overview_parser,
        "--include-categories",
        action="store_true",
        help="Include category totals in the response",
    )
    register_argument(
        query_overview_parser,
        "--include-runs",
        action="store_true",
        help="Include per-run severity totals",
    )

    query_hotspots_parser = query_sub.add_parser(
        QuerySection.HOTSPOTS.value,
        help="List top offending files or folders",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        parents=section_parents,
    )
    register_argument(
        query_hotspots_parser,
        "--kind",
        choices=[kind.value for kind in HotspotKind],
        default=HotspotKind.FILES.value,
        help="Select whether to report file or folder hotspots",
    )
    register_argument(
        query_hotspots_parser,
        "--limit",
        type=int,
        default=10,
        help="Maximum entries to return",
    )

    query_readiness_parser = query_sub.add_parser(
        QuerySection.READINESS.value,
        help="Show readiness candidates for strict typing",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        parents=section_parents,
    )
    register_readiness_flag(query_readiness_parser, default_enabled=True)

    query_runs_parser = query_sub.add_parser(
        QuerySection.RUNS.value,
        help="Inspect individual typing runs",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        parents=section_parents,
    )
    register_argument(
        query_runs_parser,
        "--tool",
        dest="tools",
        action="append",
        default=None,
        help="Filter by tool name (repeatable, e.g., pyright)",
    )
    register_argument(
        query_runs_parser,
        "--mode",
        dest="modes",
        action="append",
        default=None,
        help="Filter by mode (repeatable, e.g., current or target)",
    )
    register_argument(
        query_runs_parser,
        "--limit",
        type=int,
        default=10,
        help="Maximum runs to return",
    )

    query_engines_parser = query_sub.add_parser(
        QuerySection.ENGINES.value,
        help="Display engine configuration used for runs",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        parents=section_parents,
    )
    register_argument(
        query_engines_parser,
        "--limit",
        type=int,
        default=10,
        help="Maximum rows to return",
    )

    query_rules_parser = query_sub.add_parser(
        QuerySection.RULES.value,
        help="Show the most common rule diagnostics",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        parents=section_parents,
    )
    register_argument(
        query_rules_parser,
        "--limit",
        type=int,
        default=10,
        help="Maximum rules to return",
    )
    register_argument(
        query_rules_parser,
        "--include-paths",
        action="store_true",
        help="Include top file paths per rule",
    )


def _render_payload(data: object, fmt: DataFormat) -> None:
    for line in render_data(data, fmt):
        echo(line)


def execute_query(args: argparse.Namespace, context: CLIContext) -> int:
    """Execute the `ratchetr query` command.

    Args:
        args: Parsed CLI namespace describing the desired section and filters.
        context: Shared CLI context providing manifest resolution.

    Returns:
        `0` when the query runs successfully.

    Raises:
        SystemExit: If the section selector is invalid.
    """
    manifest_path = discover_manifest_or_exit(context, cli_manifest=getattr(args, "manifest", None))
    summary = load_summary_from_manifest(manifest_path)
    stdout_format = StdoutFormat.from_str(getattr(args, "out", StdoutFormat.TEXT.value))
    data_format = DataFormat.JSON if stdout_format is StdoutFormat.JSON else DataFormat.TABLE
    section_value = args.query_section
    try:
        section = section_value if isinstance(section_value, QuerySection) else QuerySection.from_str(section_value)
    # ignore JUSTIFIED: argparse restricts valid choices;
    # fallback branch is unreachable in normal CLI flow
    except ValueError as exc:  # pragma: no cover
        raise SystemExit(str(exc)) from exc

    match section:
        case QuerySection.OVERVIEW:
            _render_payload(
                query_overview(
                    summary,
                    include_categories=args.include_categories,
                    include_runs=args.include_runs,
                ),
                data_format,
            )
        case QuerySection.HOTSPOTS:
            kind = HotspotKind.from_str(args.kind)
            _render_payload(
                query_hotspots(summary, kind=kind, limit=args.limit),
                data_format,
            )
        case QuerySection.READINESS:
            readiness_tokens = getattr(args, "readiness", None)
            readiness = parse_readiness_tokens(readiness_tokens, flag_present=readiness_tokens is not None)
            _render_payload(
                query_readiness(
                    summary,
                    level=readiness.level,
                    statuses=list(readiness.statuses) if readiness.statuses else None,
                    limit=readiness.limit,
                    severities=list(readiness.severities) if readiness.severities else None,
                ),
                data_format,
            )
        case QuerySection.RUNS:
            _render_payload(
                query_runs(summary, tools=args.tools, modes=args.modes, limit=args.limit),
                data_format,
            )
        case QuerySection.ENGINES:
            _render_payload(
                query_engines(summary, limit=args.limit),
                data_format,
            )
        case QuerySection.RULES:
            _render_payload(
                query_rules(
                    summary,
                    limit=args.limit,
                    default_paths=bool(getattr(args, "include_paths", False)),
                ),
                data_format,
            )

    return 0


__all__ = ["execute_query", "register_query_command"]
