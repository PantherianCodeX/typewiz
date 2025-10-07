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
                "errors": 3,
                "warnings": 2,
                "information": 1,
                "total": 6,
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
                "warnings": 0,
                "information": 0,
                "total": 1,
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
        "severityTotals": {"error": 4, "warning": 2, "information": 1},
        "topRules": {"reportUnknownMemberType": 2, "reportGeneralTypeIssues": 1},
        "topFolders": [
            {
                "path": "apps/platform/operations",
                "errors": 2,
                "warnings": 1,
                "information": 0,
                "participatingRuns": 2,
            },
            {
                "path": "packages/agents",
                "errors": 1,
                "warnings": 1,
                "information": 0,
                "participatingRuns": 1,
            },
        ],
        "topFiles": [
            {"path": "apps/platform/operations/admin.py", "errors": 2, "warnings": 0},
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
        "runs": {
            "runSummary": summary["runSummary"],
        },
    }
    return summary
