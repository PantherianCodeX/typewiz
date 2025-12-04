# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

import pytest

from typewiz.core.model_types import Mode, SeverityLevel
from typewiz.core.type_aliases import RelPath, ToolName
from typewiz.core.types import Diagnostic, RunResult
from typewiz.manifest.builder import ManifestBuilder


def _make_run(tmp_path: Path) -> RunResult:
    diagnostic = Diagnostic(
        tool=ToolName("pyright"),
        severity=SeverityLevel.ERROR,
        path=tmp_path / "pkg" / "app.py",
        line=1,
        column=1,
        code="E",
        message="boom",
        raw={},
    )
    return RunResult(
        tool=ToolName("pyright"),
        mode=Mode.CURRENT,
        command=["pyright"],
        exit_code=1,
        duration_ms=10.5,
        diagnostics=[diagnostic],
        plugin_args=["--lib"],
        include=[RelPath("src")],
        exclude=[RelPath("tests")],
        overrides=[],
        category_mapping={"unknownChecks": ["foo"]},
        tool_summary={"errors": 1, "warnings": 0, "information": 0, "total": 1},
        scanned_paths=[RelPath("src")],
        engine_error={"message": "crash", "stderr": "oops", "exitCode": 2},
    )


def test_manifest_builder_adds_run_and_writes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    builder = ManifestBuilder(tmp_path)
    builder.add_run(_make_run(tmp_path))
    builder.fingerprint_truncated = True

    versions = {"pyright": "1.1.0"}

    def fake_detect_tool_versions(_: Sequence[str]) -> dict[str, str]:
        return versions

    monkeypatch.setattr("typewiz.manifest.builder.detect_tool_versions", fake_detect_tool_versions)

    output_path = tmp_path / "reports" / "typing_audit.json"
    builder.write(output_path)
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["fingerprintTruncated"] is True
    assert payload["toolVersions"] == versions
    assert payload["runs"]
