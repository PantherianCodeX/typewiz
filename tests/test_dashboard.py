# mypy: ignore-errors
# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

import copy
from collections.abc import Callable
from pathlib import Path
from typing import cast

import pytest

from typewiz.dashboard import build_summary, load_manifest, render_markdown
from typewiz.html_report import render_html
from typewiz.manifest_models import ManifestValidationError
from typewiz.manifest_versioning import CURRENT_MANIFEST_VERSION
from typewiz.summary_types import SummaryData
from typewiz.type_aliases import RunId
from typewiz.typed_manifest import FileEntry, FolderEntry, ManifestData, RunPayload
from typewiz.utils import consume


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
