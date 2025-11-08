# Copyright (c) 2024 PantherianCodeX
"""Query command implementation for the modular Typewiz CLI."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Protocol

from typewiz.dashboard import build_summary, load_manifest
from typewiz.model_types import (
    DataFormat,
    HotspotKind,
    QuerySection,
    ReadinessLevel,
    ReadinessStatus,
    SeverityLevel,
)
from typewiz.summary_types import SummaryData

from ..helpers import (
    echo,
    query_engines,
    query_hotspots,
    query_overview,
    query_readiness,
    query_rules,
    query_runs,
    register_argument,
    render_data,
)


class SubparserRegistry(Protocol):
    def add_parser(
        self, *args: Any, **kwargs: Any
    ) -> argparse.ArgumentParser: ...  # pragma: no cover - Protocol


def register_query_command(subparsers: SubparserRegistry) -> None:
    """Register the ``typewiz query`` command."""
    query = subparsers.add_parser(
        "query",
        help="Inspect sections of a manifest summary without external tools",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    query_sub = query.add_subparsers(dest="query_section", required=True)

    query_overview_parser = query_sub.add_parser(
        QuerySection.OVERVIEW.value,
        help="Show severity totals, with optional category and run breakdowns",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    _register_common_manifest_argument(query_overview_parser)
    register_argument(
        query_overview_parser,
        "--format",
        choices=[fmt.value for fmt in DataFormat],
        default=DataFormat.JSON.value,
        help="Output format",
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
    )
    _register_common_manifest_argument(query_hotspots_parser)
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
    register_argument(
        query_hotspots_parser,
        "--format",
        choices=[fmt.value for fmt in DataFormat],
        default=DataFormat.JSON.value,
        help="Output format",
    )

    query_readiness_parser = query_sub.add_parser(
        QuerySection.READINESS.value,
        help="Show readiness candidates for strict typing",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    _register_common_manifest_argument(query_readiness_parser)
    register_argument(
        query_readiness_parser,
        "--level",
        choices=[level.value for level in ReadinessLevel],
        default=ReadinessLevel.FOLDER.value,
        help="Granularity for readiness data",
    )
    register_argument(
        query_readiness_parser,
        "--status",
        dest="statuses",
        action="append",
        choices=[status.value for status in ReadinessStatus],
        default=None,
        help="Status buckets to include (repeatable)",
    )
    register_argument(
        query_readiness_parser,
        "--limit",
        type=int,
        default=10,
        help="Maximum entries per status bucket",
    )
    register_argument(
        query_readiness_parser,
        "--severity",
        dest="severities",
        action="append",
        choices=[severity.value for severity in SeverityLevel],
        default=None,
        help="Filter to severities (repeatable: error, warning, information)",
    )
    register_argument(
        query_readiness_parser,
        "--format",
        choices=[fmt.value for fmt in DataFormat],
        default=DataFormat.JSON.value,
        help="Output format",
    )

    query_runs_parser = query_sub.add_parser(
        QuerySection.RUNS.value,
        help="Inspect individual typing runs",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    _register_common_manifest_argument(query_runs_parser)
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
        help="Filter by mode (repeatable, e.g., current or full)",
    )
    register_argument(
        query_runs_parser,
        "--limit",
        type=int,
        default=10,
        help="Maximum runs to return",
    )
    register_argument(
        query_runs_parser,
        "--format",
        choices=[fmt.value for fmt in DataFormat],
        default=DataFormat.JSON.value,
        help="Output format",
    )

    query_engines_parser = query_sub.add_parser(
        QuerySection.ENGINES.value,
        help="Display engine configuration used for runs",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    _register_common_manifest_argument(query_engines_parser)
    register_argument(
        query_engines_parser,
        "--limit",
        type=int,
        default=10,
        help="Maximum rows to return",
    )
    register_argument(
        query_engines_parser,
        "--format",
        choices=[fmt.value for fmt in DataFormat],
        default=DataFormat.JSON.value,
        help="Output format",
    )

    query_rules_parser = query_sub.add_parser(
        QuerySection.RULES.value,
        help="Show the most common rule diagnostics",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    _register_common_manifest_argument(query_rules_parser)
    register_argument(
        query_rules_parser,
        "--limit",
        type=int,
        default=10,
        help="Maximum rules to return",
    )
    register_argument(
        query_rules_parser,
        "--format",
        choices=[fmt.value for fmt in DataFormat],
        default=DataFormat.JSON.value,
        help="Output format",
    )
    register_argument(
        query_rules_parser,
        "--include-paths",
        action="store_true",
        help="Include top file paths per rule",
    )


def _register_common_manifest_argument(parser: argparse.ArgumentParser) -> None:
    register_argument(
        parser,
        "--manifest",
        type=Path,
        required=True,
        help="Path to a typing audit manifest.",
    )


def _load_summary(manifest_path: Path) -> SummaryData:
    manifest = load_manifest(manifest_path)
    return build_summary(manifest)


def _render_payload(data: object, fmt: DataFormat) -> None:
    for line in render_data(data, fmt):
        echo(line)


def execute_query(args: argparse.Namespace) -> int:
    """Execute the ``typewiz query`` command."""
    summary = _load_summary(args.manifest)
    section_value = args.query_section
    try:
        section = (
            section_value
            if isinstance(section_value, QuerySection)
            else QuerySection.from_str(section_value)
        )
    except ValueError as exc:  # pragma: no cover - argparse prevents invalid choices
        raise SystemExit(str(exc)) from exc

    format_choice = DataFormat.from_str(args.format)

    payload: object
    match section:
        case QuerySection.OVERVIEW:
            payload = query_overview(
                summary,
                include_categories=args.include_categories,
                include_runs=args.include_runs,
            )
        case QuerySection.HOTSPOTS:
            kind = HotspotKind.from_str(args.kind)
            payload = query_hotspots(summary, kind=kind, limit=args.limit)
        case QuerySection.READINESS:
            level_choice = ReadinessLevel.from_str(args.level)
            statuses = (
                [ReadinessStatus.from_str(status) for status in args.statuses]
                if args.statuses
                else None
            )
            severities = (
                [SeverityLevel.from_str(severity) for severity in args.severities]
                if args.severities
                else None
            )
            payload = query_readiness(
                summary,
                level=level_choice,
                statuses=statuses,
                limit=args.limit,
                severities=severities,
            )
        case QuerySection.RUNS:
            payload = query_runs(summary, tools=args.tools, modes=args.modes, limit=args.limit)
        case QuerySection.ENGINES:
            payload = query_engines(summary, limit=args.limit)
        case QuerySection.RULES:
            payload = query_rules(
                summary,
                limit=args.limit,
                include_paths=bool(getattr(args, "include_paths", False)),
            )

    _render_payload(payload, format_choice)
    return 0


__all__ = ["execute_query", "register_query_command"]
