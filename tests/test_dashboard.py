# mypy: ignore-errors
# pyright: reportPrivateUsage=false
# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

from __future__ import annotations

import copy
from collections import Counter, defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from typewiz._internal.utils import consume
from typewiz.api import build_summary, load_manifest, render_html, render_markdown
from typewiz.core.model_types import SeverityLevel
from typewiz.core.summary_types import SummaryData
from typewiz.core.type_aliases import RelPath, RunId
from typewiz.dashboard.build import (
    _build_engine_options_payload,
    _consume_run,
    _FolderAccumulators,
    _prepare_run_payload,
    _SummaryState,
)
from typewiz.manifest.models import ManifestValidationError
from typewiz.manifest.typed import FileEntry, FolderEntry, ManifestData, RunPayload
from typewiz.manifest.versioning import CURRENT_MANIFEST_VERSION
from typewiz.runtime import JSONValue


def test_render_markdown_snapshot(
    sample_summary: SummaryData,
    snapshot_text: Callable[[str], str],
) -> None:
    output = render_markdown(sample_summary)
    assert output == snapshot_text("dashboard.md")


def test_render_html_snapshot(
    sample_summary: SummaryData,
    snapshot_text: Callable[[str], str],
) -> None:
    output = render_html(sample_summary)
    assert output == snapshot_text("dashboard.html")


def test_build_summary_minimal(tmp_path: Path) -> None:
    manifest: ManifestData = {
        "projectRoot": str(tmp_path),
        "generatedAt": "now",
        "schemaVersion": CURRENT_MANIFEST_VERSION,
        "runs": [],
    }
    summary = build_summary(manifest)
    assert summary["runSummary"] == {}
    assert summary["tabs"]["overview"]["severityTotals"] == {}


def test_load_manifest_reads_file(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    consume(
        manifest_path.write_text(
            f'{{"schemaVersion": "{CURRENT_MANIFEST_VERSION}", "runs": []}}',
            encoding="utf-8",
        ),
    )
    data = load_manifest(manifest_path)
    assert "runs" in data and data["runs"] == []


def test_load_manifest_discards_invalid_runs(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    consume(
        manifest_path.write_text(
            f'{{"schemaVersion": "{CURRENT_MANIFEST_VERSION}", "runs": ["not-a-run", 3]}}',
            encoding="utf-8",
        ),
    )
    with pytest.raises(ManifestValidationError):
        _ = load_manifest(manifest_path)


def test_build_summary_skips_missing_entries(tmp_path: Path) -> None:
    manifest: ManifestData = {
        "projectRoot": str(tmp_path),
        "generatedAt": "now",
        "schemaVersion": CURRENT_MANIFEST_VERSION,
        "runs": [
            cast(
                RunPayload,
                {
                    "tool": "stub",
                    "mode": "full",
                    "command": [],
                    "exitCode": 0,
                    "durationMs": 1,
                    "summary": {
                        "severityBreakdown": {},
                        "ruleCounts": {},
                        "categoryCounts": {},
                    },
                    "engineOptions": {},
                    "perFolder": cast(
                        list[FolderEntry],
                        [{"path": None, "errors": 1, "warnings": 1}],
                    ),
                    "perFile": cast(
                        list[FileEntry],
                        [{"path": "pkg/module.py", "errors": 0, "warnings": 0}],
                    ),
                },
            ),
        ],
    }
    summary = build_summary(manifest)
    assert summary["topFolders"] == []
    assert summary["topFiles"] == []


def test_render_markdown_handles_empty_runs(snapshot_text: Callable[[str], str]) -> None:
    manifest: ManifestData = {
        "generatedAt": "now",
        "projectRoot": ".",
        "schemaVersion": CURRENT_MANIFEST_VERSION,
        "runs": [],
    }
    summary = build_summary(manifest)
    output = render_markdown(summary)
    assert "_No runs recorded_" in output
    assert "No engine data" in output


def test_render_markdown_tool_totals_mismatch(sample_summary: SummaryData) -> None:
    summary = copy.deepcopy(sample_summary)
    run_summary = summary["tabs"]["overview"]["runSummary"]
    run_id = RunId("mypy:full")
    assert run_id in run_summary
    target = run_summary[run_id]
    target["toolSummary"] = {"errors": 2, "warnings": 0, "information": 0, "total": 2}
    output = render_markdown(summary)
    assert "mismatch vs parsed" in output


def test_prepare_run_payload_returns_expected_values() -> None:
    run_payload: dict[str, JSONValue] = {
        "tool": "pyright",
        "mode": "current",
        "command": ["pyright"],
        "summary": {"errors": 1, "warnings": 0, "information": 0, "total": 1},
        "engineOptions": {},
    }
    payload = _prepare_run_payload(run_payload)
    assert payload is not None
    run_id, summary_map, options_map, command = payload
    assert str(run_id) == "pyright:current"
    assert summary_map["errors"] == 1
    assert options_map == {}
    assert command == ["pyright"]


def test_build_engine_options_payload_normalises_lists() -> None:
    payload = _build_engine_options_payload(
        cast(
            dict[str, JSONValue],
            {
                "profile": "baseline",
                "configFile": "pyrightconfig.json",
                "pluginArgs": ["--strict"],
                "include": ["src"],
                "exclude": ["tests"],
                "overrides": [
                    {
                        "path": "src/app.py",
                        "pluginArgs": ["--strict"],
                        "include": ["src"],
                        "exclude": [],
                    },
                ],
                "categoryMapping": {"unknownChecks": ["reportMissingType"]},
            },
        )
    )
    assert payload.get("pluginArgs") == ["--strict"]
    assert payload.get("include") == [RelPath("src")]
    category_mapping = payload.get("categoryMapping") or {}
    assert category_mapping.get("unknownChecks") == ["reportMissingType"]


def test_consume_run_updates_summary_state() -> None:
    run_payload: dict[str, JSONValue] = {
        "tool": "pyright",
        "mode": "current",
        "command": ["pyright"],
        "summary": {
            "errors": 1,
            "warnings": 0,
            "information": 0,
            "total": 1,
            "severityBreakdown": {"error": 1},
            "ruleCounts": {"TEST": 1},
            "categoryCounts": {"unknownChecks": 1},
        },
        "engineOptions": {},
        "perFolder": [
            {
                "path": "src",
                "errors": 1,
                "warnings": 0,
                "information": 0,
                "codeCounts": {},
                "categoryCounts": {},
            },
        ],
        "perFile": [
            {
                "path": "src/app.py",
                "errors": 1,
                "warnings": 0,
                "information": 0,
                "diagnostics": [{"code": "TEST"}],
            }
        ],
    }
    state = _SummaryState(
        run_summary={},
        severity_totals=Counter(),
        rule_totals=Counter(),
        category_totals=Counter(),
        folder_stats=_FolderAccumulators(
            totals=defaultdict(Counter),
            counts=defaultdict(int),
            code_totals=defaultdict(Counter),
            category_totals=defaultdict(Counter),
            recommendations=defaultdict(set),
        ),
        file_entries=[],
        rule_file_counts=defaultdict(Counter),
    )
    _consume_run(run_payload, state=state)
    assert RunId("pyright:current") in state.run_summary
    assert state.severity_totals[SeverityLevel.ERROR] == 1
    assert state.folder_stats.totals["src"]["errors"] == 1
    assert state.rule_file_counts["TEST"]["src/app.py"] == 1
