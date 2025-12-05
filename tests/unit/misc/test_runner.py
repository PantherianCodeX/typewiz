# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Unit tests for Misc Runner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from typewiz._internal.utils import CommandOutput, consume
from typewiz.core.model_types import Mode, SeverityLevel
from typewiz.engines.execution import run_pyright

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

    monkeypatch.setattr("typewiz.engines.execution.run_command", _run_command)


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

    result = run_pyright(tmp_path, mode=Mode.FULL, command=["pyright", "--outputjson"])

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
        assert kwargs == {}

    monkeypatch.setattr("typewiz.engines.execution.logger.warning", fake_warning)

    result = run_pyright(tmp_path, mode=Mode.CURRENT, command=["pyright", "--outputjson"])

    assert any("pyright summary mismatch" in warning for warning in warnings)
    assert result.tool_summary == {"errors": 0, "warnings": 2, "information": 0, "total": 2}
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].severity is SeverityLevel.WARNING
