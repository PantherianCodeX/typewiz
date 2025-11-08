# pyright: reportPrivateUsage=false
# Copyright (c) 2024 PantherianCodeX

"""Unit tests for CLI helper utilities."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from typewiz.cli.helpers import (
    collect_profile_args,
    parse_comma_separated,
    parse_hash_workers,
    parse_int_mapping,
    parse_key_value_entries,
    render_data,
)
from typewiz.cli.helpers.formatting import (
    FolderHotspotEntry,
    _format_run_header,
    _paths_details,
    _profile_details,
    query_engines,
    query_hotspots,
    query_overview,
    query_readiness,
    query_rules,
    query_runs,
)
from typewiz.core.model_types import (
    DataFormat,
    HotspotKind,
    Mode,
    ReadinessLevel,
    ReadinessStatus,
    SeverityLevel,
)
from typewiz.core.summary_types import (
    CountsByCategory,
    CountsByRule,
    CountsBySeverity,
    ReadinessOptionEntry,
    ReadinessOptionsPayload,
    ReadinessTab,
    RulePathEntry,
    SummaryData,
)
from typewiz.core.type_aliases import RelPath, RunId, ToolName
from typewiz.core.types import Diagnostic, RunResult
from typewiz.readiness.views import FolderReadinessPayload


def test_parse_comma_separated_strips_entries() -> None:
    assert parse_comma_separated("foo, bar ,,,baz") == ["foo", "bar", "baz"]
    assert parse_comma_separated(None) == []


def test_parse_key_value_entries_returns_pairs() -> None:
    pairs = parse_key_value_entries(["runner=strict", "mypy = baseline"], argument="--profile")
    assert pairs == [("runner", "strict"), ("mypy", "baseline")]


def test_parse_key_value_entries_rejects_invalid() -> None:
    with pytest.raises(SystemExit):
        _ = parse_key_value_entries(["novalue"], argument="--profile")


def test_parse_int_mapping_converts_to_ints() -> None:
    mapping = parse_int_mapping(["errors=1", "warnings=0"], argument="--target")
    assert mapping == {"errors": 1, "warnings": 0}


def test_parse_int_mapping_rejects_non_int() -> None:
    with pytest.raises(SystemExit):
        _ = parse_int_mapping(["errors=abc"], argument="--target")


def test_collect_profile_args_uses_helper() -> None:
    result = collect_profile_args(["pyright=baseline"])
    assert result == {"pyright": "baseline"}


def test_parse_hash_workers_accepts_values() -> None:
    assert parse_hash_workers("4") == 4
    assert parse_hash_workers("auto") == "auto"
    assert parse_hash_workers(None) is None


def test_parse_hash_workers_rejects_invalid() -> None:
    with pytest.raises(SystemExit):
        _ = parse_hash_workers("-1")
    with pytest.raises(SystemExit):
        _ = parse_hash_workers("fast")


def test_render_data_accepts_enum() -> None:
    rows = render_data({"key": "value"}, DataFormat.TABLE)
    assert rows[0].startswith("key")


def test_query_overview_payload_shapes() -> None:
    summary = _sample_summary()
    payload = query_overview(summary, include_categories=True, include_runs=True)
    assert payload["severity_totals"]["error"] == 2
    assert payload.get("category_totals", {})["unknownChecks"] == 2
    runs = payload.get("runs")
    assert runs and runs[0]["run"] == "pyright:current"


def test_query_hotspots_file_payload() -> None:
    summary = _sample_summary()
    entries = query_hotspots(summary, kind=HotspotKind.FILES, limit=1)
    assert entries[0]["path"] == "src/app.py"
    folders = cast(
        list[FolderHotspotEntry], query_hotspots(summary, kind=HotspotKind.FOLDERS, limit=1)
    )
    assert folders[0]["participating_runs"] == 1


def test_query_runs_and_engines_payloads() -> None:
    summary = _sample_summary()
    runs = query_runs(summary, tools=["pyright"], modes=["current"], limit=5)
    assert runs[0]["command"] == "pyright --strict"
    engines = query_engines(summary, limit=5)
    assert engines[0]["plugin_args"] == ["--strict"]


def test_query_rules_include_paths() -> None:
    summary = _sample_summary()
    entries = query_rules(summary, limit=1, include_paths=True)
    paths = entries[0].get("paths")
    assert paths is not None
    assert paths[0]["path"] == "src/app.py"


def test_query_readiness_payload() -> None:
    summary = _sample_summary()
    view = cast(
        dict[ReadinessStatus, list[FolderReadinessPayload]],
        query_readiness(
            summary,
            level=ReadinessLevel.FOLDER,
            statuses=[ReadinessStatus.BLOCKED],
            limit=5,
        ),
    )
    assert ReadinessStatus.BLOCKED in view
    assert view[ReadinessStatus.BLOCKED][0]["path"] == "src"


def test_format_run_header_includes_counts() -> None:
    run = _sample_run_result()
    header = _format_run_header(run)
    assert "pyright:current" in header
    assert "errors=1" in header


def test_profile_and_path_details_respect_expanded_flag() -> None:
    run = _sample_run_result()
    profile_details = dict(_profile_details(run, expanded=False))
    assert profile_details["profile"] == "strict"
    path_details = dict(_paths_details(run, expanded=False))
    assert path_details["include"] == "src"
    assert path_details["exclude"] == "tests"


def _sample_summary() -> SummaryData:
    readiness_tab: ReadinessTab = {
        "strict": {
            ReadinessStatus.BLOCKED: [
                {
                    "path": "src/app.py",
                    "diagnostics": 2,
                    "errors": 1,
                    "warnings": 1,
                    "information": 0,
                }
            ],
            ReadinessStatus.READY: [],
            ReadinessStatus.CLOSE: [],
        },
        "options": {
            "unknownChecks": ReadinessOptionsPayload(
                threshold=1,
                buckets={
                    ReadinessStatus.BLOCKED: (
                        ReadinessOptionEntry(path="src", count=2, errors=1, warnings=1),
                    ),
                },
            ),
        },
    }
    severity_totals: CountsBySeverity = {SeverityLevel.ERROR: 2}
    category_totals: CountsByCategory = {"unknownChecks": 2}
    top_rules: CountsByRule = {}
    summary: SummaryData = {
        "generatedAt": "now",
        "projectRoot": "/repo",
        "severityTotals": severity_totals,
        "categoryTotals": category_totals,
        "runSummary": {},
        "topFolders": [],
        "topFiles": [],
        "topRules": top_rules,
        "ruleFiles": {
            "reportGeneralTypeIssues": [RulePathEntry(path="src/app.py", count=2)],
        },
        "tabs": {
            "overview": {
                "severityTotals": severity_totals,
                "categoryTotals": category_totals,
                "runSummary": {
                    RunId("pyright:current"): {
                        "errors": 1,
                        "warnings": 0,
                        "information": 1,
                        "total": 2,
                    }
                },
            },
            "hotspots": {
                "topFiles": [
                    {
                        "path": "src/app.py",
                        "errors": 1,
                        "warnings": 0,
                        "information": 0,
                    }
                ],
                "topFolders": [
                    {
                        "path": "src",
                        "errors": 1,
                        "warnings": 0,
                        "information": 1,
                        "participatingRuns": 1,
                        "codeCounts": {"reportGeneralTypeIssues": 1},
                        "recommendations": ["add types"],
                    }
                ],
                "topRules": {"reportGeneralTypeIssues": 2},
                "ruleFiles": {
                    "reportGeneralTypeIssues": [RulePathEntry(path="src/app.py", count=2)],
                },
            },
            "readiness": readiness_tab,
            "runs": {
                "runSummary": {
                    RunId("pyright:current"): {
                        "errors": 1,
                        "warnings": 0,
                        "information": 1,
                        "command": ["pyright", "--strict"],
                    }
                }
            },
            "engines": {
                "runSummary": {
                    RunId("pyright:current"): {
                        "engineOptions": {
                            "profile": "strict",
                            "configFile": "pyrightconfig.json",
                            "pluginArgs": ["--strict"],
                            "include": [RelPath("src")],
                            "exclude": [],
                            "overrides": [],
                        }
                    }
                }
            },
        },
    }
    return summary


def _sample_run_result() -> RunResult:
    diagnostic = Diagnostic(
        tool=ToolName("pyright"),
        severity=SeverityLevel.ERROR,
        path=Path("src/app.py"),
        line=1,
        column=1,
        code="E100",
        message="boom",
    )
    run = RunResult(
        tool=ToolName("pyright"),
        mode=Mode.CURRENT,
        command=["pyright", "--strict"],
        exit_code=1,
        duration_ms=1.0,
        diagnostics=[diagnostic],
        profile="strict",
        config_file=Path("pyrightconfig.json"),
    )
    run.plugin_args = ["--strict"]
    run.include = [RelPath("src")]
    run.exclude = [RelPath("tests")]
    return run
