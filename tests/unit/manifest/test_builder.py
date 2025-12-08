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

"""Unit tests for Manifest Builder."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from ratchetr.core.model_types import Mode, SeverityLevel
from ratchetr.core.type_aliases import RelPath, ToolName
from ratchetr.core.types import Diagnostic, RunResult
from ratchetr.manifest.builder import ManifestBuilder

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

pytestmark = pytest.mark.unit


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


def test_manifest_builder_adds_run_and_writes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    builder = ManifestBuilder(tmp_path)
    builder.add_run(_make_run(tmp_path))
    builder.fingerprint_truncated = True

    versions = {"pyright": "1.1.0"}

    def fake_detect_tool_versions(_: Sequence[str]) -> dict[str, str]:
        return versions

    monkeypatch.setattr("ratchetr.manifest.builder.detect_tool_versions", fake_detect_tool_versions)

    output_path = tmp_path / "reports" / "typing_audit.json"
    builder.write(output_path)
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["fingerprintTruncated"] is True
    assert payload["toolVersions"] == versions
    assert payload["runs"]


def test_manifest_builder_includes_engine_error_details(tmp_path: Path) -> None:
    builder = ManifestBuilder(tmp_path)
    builder.add_run(_make_run(tmp_path))
    run_payload = builder.data["runs"][0]
    engine_err = run_payload.get("engineError", {})
    assert engine_err["message"] == "crash"
    assert engine_err["stderr"] == "oops"
    assert engine_err["exitCode"] == 2
