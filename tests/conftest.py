from __future__ import annotations

from pathlib import Path
import sys
from typing import Callable, Dict, List

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pytest

from typewiz.typed_manifest import ManifestData


@pytest.fixture
def snapshots_dir() -> Path:
    return Path(__file__).parent / "snapshots"


@pytest.fixture
def snapshot_text(snapshots_dir: Path) -> Callable[[str], str]:
    def loader(name: str) -> str:
        path = snapshots_dir / name
        if not path.exists():
            raise AssertionError(f"Snapshot {name} missing at {path}")
        return path.read_text(encoding="utf-8")

    return loader


@pytest.fixture
def sample_summary() -> dict:
    summary = {
        "generatedAt": "2025-01-01T00:00:00Z",
        "projectRoot": "/repo",
        "runSummary": {
            "pyright:current": {
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
                    "overrides": [
                        {
                            "path": "apps/platform",
                            "pluginArgs": ["--warnings"],
                        }
                    ],
                },
            },
            "mypy:full": {
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
                    "overrides": [
                        {
                            "path": "packages/legacy",
                            "exclude": ["packages/legacy"],
                        }
                    ],
                },
            },
        },
        "severityTotals": {"error": 1, "warning": 1, "information": 0},
        "topRules": {"reportUnknownMemberType": 1, "reportGeneralTypeIssues": 1},
        "topFolders": [
            {
                "path": "apps/platform/operations",
                "errors": 0,
                "warnings": 0,
                "information": 0,
                "participatingRuns": 1,
                "codeCounts": {},
                "recommendations": ["strict-ready"],
            },
            {
                "path": "packages/agents",
                "errors": 1,
                "warnings": 1,
                "information": 0,
                "participatingRuns": 1,
                "codeCounts": {"reportUnknownParameterType": 1},
                "recommendations": ["resolve 1 unknown-type issues"],
            },
        ],
        "topFiles": [
            {"path": "apps/platform/operations/admin.py", "errors": 0, "warnings": 0},
            {"path": "packages/core/agents.py", "errors": 1, "warnings": 1},
        ],
    }
    summary["tabs"] = {
        "overview": {
            "severityTotals": summary["severityTotals"],
            "runSummary": summary["runSummary"],
        },
        "engines": {
            "runSummary": summary["runSummary"],
        },
        "hotspots": {
            "topRules": summary["topRules"],
            "topFolders": summary["topFolders"],
            "topFiles": summary["topFiles"],
        },
        "readiness": {
            "strict": {
                "ready": [
                    {
                        "path": "apps/platform/operations",
                        "errors": 0,
                        "warnings": 0,
                        "information": 0,
                        "diagnostics": 0,
                        "categories": {"unknownChecks": 0, "optionalChecks": 0, "unusedSymbols": 0, "general": 0},
                        "categoryStatus": {"unknownChecks": "ready", "optionalChecks": "ready", "unusedSymbols": "ready", "general": "ready"},
                        "recommendations": ["strict-ready"],
                    }
                ],
                "close": [
                    {
                        "path": "packages/agents",
                        "errors": 1,
                        "warnings": 1,
                        "information": 0,
                        "diagnostics": 2,
                        "categories": {"unknownChecks": 1, "optionalChecks": 0, "unusedSymbols": 0, "general": 0},
                        "categoryStatus": {"unknownChecks": "close", "optionalChecks": "ready", "unusedSymbols": "ready", "general": "ready"},
                        "recommendations": ["resolve 1 unknown-type issues"],
                        "notes": ["unknownChecks: 1"],
                    }
                ],
                "blocked": [],
            },
            "options": {
                "unknownChecks": {
                    "ready": [{"path": "apps/platform/operations", "count": 0, "errors": 0, "warnings": 0}],
                    "close": [{"path": "packages/agents", "count": 1, "errors": 1, "warnings": 1}],
                    "blocked": [],
                    "threshold": 2,
                },
                "optionalChecks": {
                    "ready": [{"path": "apps/platform/operations", "count": 0, "errors": 0, "warnings": 0}],
                    "close": [],
                    "blocked": [],
                    "threshold": 2,
                },
                "unusedSymbols": {
                    "ready": [{"path": "apps/platform/operations", "count": 0, "errors": 0, "warnings": 0}],
                    "close": [],
                    "blocked": [],
                    "threshold": 4,
                },
                "general": {
                    "ready": [{"path": "apps/platform/operations", "count": 0, "errors": 0, "warnings": 0}],
                    "close": [],
                    "blocked": [],
                    "threshold": 5,
                },
            },
        },
        "runs": {
            "runSummary": summary["runSummary"],
        },
    }
    return summary
