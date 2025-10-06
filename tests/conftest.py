from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List

import pytest

from typing_inspector.typed_manifest import ManifestData


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
    return {
        "generatedAt": "2025-01-01T00:00:00Z",
        "projectRoot": "/repo",
        "runSummary": {
            "pyright:current": {
                "command": ["pyright", "--outputjson"],
                "errors": 3,
                "warnings": 2,
                "information": 1,
                "total": 6,
            },
            "mypy:full": {
                "command": ["python", "-m", "mypy"],
                "errors": 1,
                "warnings": 0,
                "information": 0,
                "total": 1,
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
