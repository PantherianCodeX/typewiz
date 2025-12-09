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

"""Unit tests for Ratchet Schema."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

from ratchetr.compat import TypedDict
from ratchetr.core.model_types import SeverityLevel
from ratchetr.core.type_aliases import RelPath
from ratchetr.ratchet.core import build_ratchet_from_manifest

if TYPE_CHECKING:
    from ratchetr.manifest.typed import (
        EngineOptionsEntry,
        FileEntry,
        ManifestData,
        RunPayload,
        RunSummary,
    )

pytestmark = [pytest.mark.unit, pytest.mark.ratchet]

REPO_ROOT = Path(__file__).resolve().parents[3]


class _DiagnosticDict(TypedDict, total=False):
    line: int
    column: int
    severity: str
    code: str | None
    message: str


def _schema_path() -> Path:
    return REPO_ROOT / "schemas" / "ratchet.schema.json"


def _load_schema() -> dict[str, object]:
    return cast("dict[str, object]", json.loads(_schema_path().read_text()))


def _manifest() -> ManifestData:
    per_file_counts = {"src/app.py": Counter({"error": 1, "warning": 1})}
    per_file_entries: list[FileEntry] = []
    for path, counts in per_file_counts.items():
        diagnostics: list[_DiagnosticDict] = []
        for severity, count in counts.items():
            diagnostics.extend(
                {
                    "line": 1,
                    "column": 1,
                    "severity": severity,
                    "code": f"{severity}:{index}",
                    "message": f"{severity} {index}",
                }
                for index in range(count)
            )
        per_file_entries.append(
            cast(
                "FileEntry",
                {
                    "path": path,
                    "errors": counts.get("error", 0),
                    "warnings": counts.get("warning", 0),
                    "information": counts.get("information", 0),
                    "diagnostics": diagnostics,
                },
            )
        )
    engine_options: EngineOptionsEntry = {
        "profile": "baseline",
        "pluginArgs": ["--strict"],
        "include": [RelPath("src")],
        "exclude": [],
    }
    summary_totals = cast(
        "RunSummary",
        {
            "errors": 1,
            "warnings": 1,
            "information": 0,
            "total": 2,
            "severityBreakdown": {},
            "ruleCounts": {},
            "categoryCounts": {},
        },
    )
    run_payload = cast(
        "RunPayload",
        {
            "tool": "pyright",
            "mode": "current",
            "command": ["pyright", "--strict"],
            "exitCode": 0,
            "durationMs": 1.0,
            "summary": summary_totals,
            "perFile": per_file_entries,
            "perFolder": [],
            "engineOptions": engine_options,
        },
    )
    return cast(
        "ManifestData",
        {
            "generatedAt": "2025-01-01T00:00:00Z",
            "projectRoot": "/repo",
            "runs": [run_payload],
        },
    )


@pytest.mark.parametrize("validator_name", ["Draft7Validator", "Draft202012Validator"])
def test_ratchet_schema_validates_sample(validator_name: str) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = _load_schema()
    validator_cls = getattr(jsonschema, validator_name)
    validator = validator_cls(schema)
    ratchet_model = build_ratchet_from_manifest(
        manifest=_manifest(),
        runs=None,
        severities=[SeverityLevel.ERROR, SeverityLevel.WARNING],
        targets={"error": 0},
        manifest_path="typing_audit.json",
    )
    payload = ratchet_model.model_dump(by_alias=True, mode="json")
    validator.validate(payload)
