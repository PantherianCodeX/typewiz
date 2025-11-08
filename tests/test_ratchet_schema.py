from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import TypedDict, cast

import pytest

from typewiz.core.model_types import SeverityLevel
from typewiz.core.type_aliases import RelPath
from typewiz.manifest.typed import (
    EngineOptionsEntry,
    FileEntry,
    ManifestData,
    RunPayload,
    RunSummary,
)
from typewiz.ratchet.core import build_ratchet_from_manifest


class _DiagnosticDict(TypedDict, total=False):
    line: int
    column: int
    severity: str
    code: str | None
    message: str


def _schema_path() -> Path:
    return Path(__file__).parents[1] / "schemas" / "ratchet.schema.json"


def _load_schema() -> dict[str, object]:
    return cast(dict[str, object], json.loads(_schema_path().read_text()))


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
                FileEntry,
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
        RunSummary,
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
        RunPayload,
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
        ManifestData,
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
