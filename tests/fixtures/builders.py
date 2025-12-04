# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Test data builders live here until dedicated modules are created."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from typewiz._internal.utils import consume
from typewiz.core.model_types import ReadinessStatus
from typewiz.core.summary_types import (
    CountsByCategory,
    CountsByRule,
    CountsBySeverity,
    EnginesTab,
    HotspotsTab,
    OverviewTab,
    ReadinessTab,
    RunsTab,
    SummaryData,
    SummaryFileEntry,
    SummaryFolderEntry,
    SummaryRunEntry,
    SummaryTabs,
)
from typewiz.core.type_aliases import RelPath, RunId
from typewiz.manifest.versioning import CURRENT_MANIFEST_VERSION

__all__ = ["build_cli_manifest", "build_empty_summary"]


def build_cli_manifest(tmp_path: Path) -> Path:
    """Generate a representative CLI manifest for integration tests."""
    manifest: dict[str, Any] = {
        "generatedAt": "2025-11-05T00:00:00Z",
        "projectRoot": str(tmp_path),
        "schemaVersion": CURRENT_MANIFEST_VERSION,
        "runs": [
            {
                "tool": "pyright",
                "mode": "current",
                "command": ["pyright", "--project"],
                "exitCode": 1,
                "durationMs": 12,
                "summary": {
                    "errors": 4,
                    "warnings": 2,
                    "information": 0,
                    "total": 6,
                    "severityBreakdown": {"error": 4, "warning": 2},
                    "ruleCounts": {"reportGeneralTypeIssues": 4},
                    "categoryCounts": {"unknownChecks": 4},
                },
                "engineOptions": {
                    "profile": "strict",
                    "configFile": "pyrightconfig.json",
                    "pluginArgs": ["--strict"],
                    "include": [RelPath("src")],
                    "exclude": [RelPath("tests")],
                    "overrides": [{"path": "src", "profile": "strict"}],
                    "categoryMapping": {"unknownChecks": ["reportGeneralTypeIssues"]},
                },
                "perFolder": [
                    {
                        "path": "src",
                        "depth": 1,
                        "errors": 3,
                        "warnings": 2,
                        "information": 0,
                        "codeCounts": {"reportGeneralTypeIssues": 4},
                        "categoryCounts": {"unknownChecks": 4},
                        "recommendations": ["add type annotations"],
                    },
                ],
                "perFile": [
                    {
                        "path": "src/app.py",
                        "errors": 3,
                        "warnings": 0,
                        "information": 0,
                        "diagnostics": [
                            {
                                "line": 10,
                                "column": 4,
                                "severity": "error",
                                "code": "reportGeneralTypeIssues",
                                "message": "strict mode failure",
                            },
                        ],
                    },
                    {
                        "path": "src/utils.py",
                        "errors": 0,
                        "warnings": 2,
                        "information": 0,
                        "diagnostics": [
                            {
                                "line": 20,
                                "column": 2,
                                "severity": "warning",
                                "code": "reportUnknownVariableType",
                                "message": "graduated warning",
                            },
                        ],
                    },
                ],
            },
            {
                "tool": "mypy",
                "mode": "full",
                "command": ["mypy", "--strict"],
                "exitCode": 0,
                "durationMs": 15,
                "summary": {
                    "errors": 0,
                    "warnings": 1,
                    "information": 1,
                    "total": 2,
                    "severityBreakdown": {"warning": 1, "information": 1},
                    "ruleCounts": {"attr-defined": 1},
                    "categoryCounts": {"general": 1},
                },
                "engineOptions": {
                    "profile": "baseline",
                    "configFile": "mypy.ini",
                    "pluginArgs": [],
                    "include": [RelPath("src")],
                    "exclude": [],
                    "overrides": [],
                    "categoryMapping": {},
                },
                "perFolder": [
                    {
                        "path": "src",
                        "depth": 1,
                        "errors": 0,
                        "warnings": 1,
                        "information": 1,
                        "codeCounts": {"attr-defined": 1},
                        "categoryCounts": {"general": 1},
                        "recommendations": [],
                    },
                ],
                "perFile": [
                    {
                        "path": "src/app.py",
                        "errors": 0,
                        "warnings": 1,
                        "information": 1,
                        "diagnostics": [
                            {
                                "line": 30,
                                "column": 6,
                                "severity": "warning",
                                "code": "attr-defined",
                                "message": "attr-defined warning",
                            },
                        ],
                    },
                ],
            },
        ],
    }
    manifest_path = tmp_path / "manifest.json"
    consume(manifest_path.write_text(json.dumps(manifest), encoding="utf-8"))
    return manifest_path


def build_empty_summary() -> SummaryData:
    """Construct a blank SummaryData payload with the required structure."""
    run_summary: dict[RunId, SummaryRunEntry] = {}
    severity_totals: CountsBySeverity = {}
    category_totals: CountsByCategory = {}
    top_rules: CountsByRule = {}
    overview: OverviewTab = {
        "severityTotals": severity_totals,
        "categoryTotals": category_totals,
        "runSummary": run_summary,
    }
    engines: EnginesTab = {"runSummary": run_summary}
    top_folders: list[SummaryFolderEntry] = []
    top_files: list[SummaryFileEntry] = []
    hotspots: HotspotsTab = {
        "topRules": top_rules,
        "topFolders": top_folders,
        "topFiles": top_files,
        "ruleFiles": {},
    }
    readiness: ReadinessTab = {
        "strict": {
            ReadinessStatus.READY: [],
            ReadinessStatus.CLOSE: [],
            ReadinessStatus.BLOCKED: [],
        },
        "options": {},
    }
    runs: RunsTab = {"runSummary": run_summary}
    tabs: SummaryTabs = {
        "overview": overview,
        "engines": engines,
        "hotspots": hotspots,
        "readiness": readiness,
        "runs": runs,
    }
    summary: SummaryData = {
        "generatedAt": "now",
        "projectRoot": ".",
        "runSummary": run_summary,
        "severityTotals": severity_totals,
        "categoryTotals": category_totals,
        "topRules": top_rules,
        "topFolders": top_folders,
        "topFiles": top_files,
        "ruleFiles": {},
        "tabs": tabs,
    }
    return summary
