from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pytest

from typewiz.model_types import OverrideEntry, ReadinessStatus, SeverityLevel
from typewiz.summary_types import (
    CountsByCategory,
    CountsBySeverity,
    ReadinessOptionEntry,
    ReadinessOptionsPayload,
    ReadinessStrictEntry,
    ReadinessTab,
    SummaryData,
    SummaryFileEntry,
    SummaryFolderEntry,
    SummaryRunEntry,
    SummaryTabs,
)
from typewiz.type_aliases import CategoryName, RunId


class SnapshotMissingError(AssertionError):
    """Raised when an expected snapshot fixture is missing."""

    def __init__(self, name: str, path: Path) -> None:
        self.name = name
        self.path = path
        super().__init__(f"Snapshot {name} missing at {path}")


@pytest.fixture
def snapshots_dir() -> Path:
    return Path(__file__).parent / "snapshots"


@pytest.fixture
def snapshot_text(snapshots_dir: Path) -> Callable[[str], str]:
    def loader(name: str) -> str:
        path = snapshots_dir / name
        if not path.exists():
            raise SnapshotMissingError(name, path)
        return path.read_text(encoding="utf-8")

    return loader


@pytest.fixture
def sample_summary() -> SummaryData:
    pyright_override: OverrideEntry = {"path": "apps/platform", "pluginArgs": ["--warnings"]}
    mypy_override: OverrideEntry = {"path": "packages/legacy", "exclude": ["packages/legacy"]}

    pyright_run: SummaryRunEntry = {
        "command": ["pyright", "--outputjson"],
        "errors": 0,
        "warnings": 0,
        "information": 0,
        "total": 0,
        "engineOptions": {
            "profile": "baseline",
            "configFile": "pyrightconfig.json",
            "pluginArgs": ["--lib"],
            "include": ["apps"],
            "exclude": ["apps/legacy"],
            "overrides": [pyright_override],
        },
    }
    mypy_run: SummaryRunEntry = {
        "command": ["python", "-m", "mypy"],
        "errors": 1,
        "warnings": 1,
        "information": 0,
        "total": 2,
        "engineOptions": {
            "profile": "strict",
            "configFile": "mypy.ini",
            "pluginArgs": ["--strict"],
            "include": ["packages"],
            "exclude": [],
            "overrides": [mypy_override],
        },
    }
    run_summary: dict[RunId, SummaryRunEntry] = {
        RunId("pyright:current"): pyright_run,
        RunId("mypy:full"): mypy_run,
    }

    severity_totals: CountsBySeverity = {
        SeverityLevel.ERROR: 1,
        SeverityLevel.WARNING: 1,
        SeverityLevel.INFORMATION: 0,
    }
    top_rules: dict[str, int] = {
        "reportUnknownMemberType": 1,
        "reportGeneralTypeIssues": 1,
    }
    ready_code_counts: dict[str, int] = {}
    agent_code_counts: dict[str, int] = {"reportUnknownParameterType": 1}
    top_folders: list[SummaryFolderEntry] = [
        {
            "path": "apps/platform/operations",
            "errors": 0,
            "warnings": 0,
            "information": 0,
            "participatingRuns": 1,
            "codeCounts": ready_code_counts,
            "recommendations": ["strict-ready"],
        },
        {
            "path": "packages/agents",
            "errors": 1,
            "warnings": 1,
            "information": 0,
            "participatingRuns": 1,
            "codeCounts": agent_code_counts,
            "recommendations": ["resolve 1 unknown-type issues"],
        },
    ]
    top_files: list[SummaryFileEntry] = [
        {"path": "apps/platform/operations/admin.py", "errors": 0, "warnings": 0},
        {"path": "packages/core/agents.py", "errors": 1, "warnings": 1},
    ]

    readiness_ready_categories: dict[CategoryName, int] = {
        CategoryName("unknownChecks"): 0,
        CategoryName("optionalChecks"): 0,
        CategoryName("unusedSymbols"): 0,
        CategoryName("general"): 0,
    }
    readiness_ready_status: dict[CategoryName, ReadinessStatus] = {
        CategoryName("unknownChecks"): ReadinessStatus.READY,
        CategoryName("optionalChecks"): ReadinessStatus.READY,
        CategoryName("unusedSymbols"): ReadinessStatus.READY,
        CategoryName("general"): ReadinessStatus.READY,
    }
    readiness_ready: list[ReadinessStrictEntry] = [
        {
            "path": "apps/platform/operations",
            "errors": 0,
            "warnings": 0,
            "information": 0,
            "diagnostics": 0,
            "categories": readiness_ready_categories,
            "categoryStatus": readiness_ready_status,
            "recommendations": ["strict-ready"],
        },
    ]
    readiness_close_categories: dict[CategoryName, int] = {
        CategoryName("unknownChecks"): 1,
        CategoryName("optionalChecks"): 0,
        CategoryName("unusedSymbols"): 0,
        CategoryName("general"): 0,
    }
    readiness_close_status: dict[CategoryName, ReadinessStatus] = {
        CategoryName("unknownChecks"): ReadinessStatus.CLOSE,
        CategoryName("optionalChecks"): ReadinessStatus.READY,
        CategoryName("unusedSymbols"): ReadinessStatus.READY,
        CategoryName("general"): ReadinessStatus.READY,
    }
    readiness_close: list[ReadinessStrictEntry] = [
        {
            "path": "packages/agents",
            "errors": 1,
            "warnings": 1,
            "information": 0,
            "diagnostics": 2,
            "categories": readiness_close_categories,
            "categoryStatus": readiness_close_status,
            "recommendations": ["resolve 1 unknown-type issues"],
            "notes": ["unknownChecks: 1"],
        },
    ]

    def _bucket(
        ready: list[ReadinessOptionEntry],
        close: list[ReadinessOptionEntry],
        *,
        threshold: int,
    ) -> ReadinessOptionsPayload:
        buckets: dict[ReadinessStatus, tuple[ReadinessOptionEntry, ...]] = {}
        if ready:
            buckets[ReadinessStatus.READY] = tuple(ready)
        if close:
            buckets[ReadinessStatus.CLOSE] = tuple(close)
        return {
            "threshold": threshold,
            "buckets": buckets,
        }

    readiness_tab: ReadinessTab = {
        "strict": {
            ReadinessStatus.READY: readiness_ready,
            ReadinessStatus.CLOSE: readiness_close,
            ReadinessStatus.BLOCKED: [],
        },
        "options": {
            "unknownChecks": _bucket(
                ready=[
                    {"path": "apps/platform/operations", "count": 0, "errors": 0, "warnings": 0},
                ],
                close=[{"path": "packages/agents", "count": 1, "errors": 1, "warnings": 1}],
                threshold=2,
            ),
            "optionalChecks": _bucket(
                ready=[
                    {"path": "apps/platform/operations", "count": 0, "errors": 0, "warnings": 0},
                ],
                close=[],
                threshold=2,
            ),
            "unusedSymbols": _bucket(
                ready=[
                    {"path": "apps/platform/operations", "count": 0, "errors": 0, "warnings": 0},
                ],
                close=[],
                threshold=4,
            ),
            "general": _bucket(
                ready=[
                    {"path": "apps/platform/operations", "count": 0, "errors": 0, "warnings": 0},
                ],
                close=[],
                threshold=5,
            ),
        },
    }

    category_totals: CountsByCategory = {}
    tabs: SummaryTabs = {
        "overview": {
            "severityTotals": severity_totals,
            "categoryTotals": category_totals,
            "runSummary": run_summary,
        },
        "engines": {"runSummary": run_summary},
        "hotspots": {
            "topRules": top_rules,
            "topFolders": top_folders,
            "topFiles": top_files,
        },
        "readiness": readiness_tab,
        "runs": {"runSummary": run_summary},
    }

    summary: SummaryData = {
        "generatedAt": "2025-01-01T00:00:00Z",
        "projectRoot": "/repo",
        "runSummary": run_summary,
        "severityTotals": severity_totals,
        "categoryTotals": category_totals,
        "topRules": top_rules,
        "topFolders": top_folders,
        "topFiles": top_files,
        "tabs": tabs,
    }
    return summary
