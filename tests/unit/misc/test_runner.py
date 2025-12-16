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

"""Unit tests for Misc Runner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from ratchetr._infra.utils import CommandOutput, consume
from ratchetr.core.model_types import Mode, SeverityLevel
from ratchetr.engines.execution import run_pyright

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

pytestmark = pytest.mark.unit


def _command_output(payload: Mapping[str, object], *, exit_code: int = 1) -> CommandOutput:
    return CommandOutput(
        args=["pyright", "--outputjson"],
        stdout=json.dumps(payload),
        stderr="",
        exit_code=exit_code,
        duration_ms=12.5,
    )


def _patch_run_command(
    monkeypatch: pytest.MonkeyPatch,
    payload: Mapping[str, object],
    *,
    exit_code: int = 1,
) -> None:
    def _run_command(
        args: Sequence[str],
        cwd: Path | None = None,
        *,
        allowed: set[str] | None = None,
    ) -> CommandOutput:
        assert args
        if cwd is not None:
            assert isinstance(cwd, Path)
        if allowed is not None:
            assert isinstance(allowed, set)
        return _command_output(payload, exit_code=exit_code)

    monkeypatch.setattr("ratchetr.engines.execution.run_command", _run_command)


def test_run_pyright_records_tool_summary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    diagnostics = [
        {
            "file": str(tmp_path / "pkg" / "module.py"),
            "severity": "error",
            "message": "failure",
            "rule": "reportGeneralTypeIssues",
            "range": {"start": {"line": 4, "character": 1}},
        },
    ]
    payload = {
        "summary": {"errorCount": 1, "warningCount": 0, "informationCount": 0},
        "generalDiagnostics": diagnostics,
    }
    (tmp_path / "pkg").mkdir(parents=True, exist_ok=True)
    consume((tmp_path / "pkg" / "module.py").write_text("x = 1\n", encoding="utf-8"))
    _patch_run_command(monkeypatch, payload)

    result = run_pyright(tmp_path, mode=Mode.TARGET, command=["pyright", "--outputjson"])

    assert result.tool_summary == {"errors": 1, "warnings": 0, "information": 0, "total": 1}
    assert len(result.diagnostics) == 1
    first = result.diagnostics[0]
    assert first.severity is SeverityLevel.ERROR
    assert first.code == "reportGeneralTypeIssues"
    assert first.line == 5  # pyright reports zero-based lines
    assert first.path == Path("pkg/module.py")


def test_run_pyright_logs_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    diagnostics = [
        {
            "filePath": str(tmp_path / "pkg" / "module.py"),
            "severity": "warning",
            "message": "issue",
            "rule": "reportUnknownArgumentType",
            "range": {"start": {"line": 0, "character": 0}},
        },
    ]
    payload = {
        "summary": {"errorCount": 0, "warningCount": 2, "informationCount": 0},
        "generalDiagnostics": diagnostics,
    }
    (tmp_path / "pkg").mkdir(parents=True, exist_ok=True)
    consume((tmp_path / "pkg" / "module.py").write_text("x = 1\n", encoding="utf-8"))
    _patch_run_command(monkeypatch, payload)
    warnings: list[str] = []

    def fake_warning(message: str, *args: object, **kwargs: object) -> None:
        if args:
            warnings.append(message % args)
        else:
            warnings.append(message)
        # Allow structured logging extras; this test only cares about the message.
        assert not kwargs or set(kwargs.keys()) <= {"extra"}

    monkeypatch.setattr("ratchetr.engines.execution.logger.warning", fake_warning)

    result = run_pyright(tmp_path, mode=Mode.CURRENT, command=["pyright", "--outputjson"])

    assert any("pyright summary mismatch" in warning for warning in warnings)
    assert result.tool_summary == {"errors": 0, "warnings": 2, "information": 0, "total": 2}
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].severity is SeverityLevel.WARNING
