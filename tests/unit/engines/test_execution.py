# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

from __future__ import annotations

import json
from collections.abc import Sequence, Set
from pathlib import Path

import pytest

from typewiz.core.model_types import Mode, SeverityLevel
from typewiz.engines.execution import run_mypy, run_pyright

pytestmark = [pytest.mark.unit, pytest.mark.engine]


class _CommandResult:
    def __init__(self, *, stdout: str = "", stderr: str = "", exit_code: int = 0) -> None:
        super().__init__()
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.duration_ms = 12.5


def test_run_pyright_parses_payload_and_warns_on_summary_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    payload = {
        "generalDiagnostics": [
            {
                "filePath": str(tmp_path / "pkg/app.py"),
                "range": {"start": {"line": 0, "character": 1}},
                "severity": "error",
                "message": "boom",
                "rule": "reportUnknown",
            },
        ],
        "summary": {"errorCount": 2, "warningCount": 0, "informationCount": 0},
    }
    captured_warning: dict[str, tuple[int, int, int, int, int, int]] = {}

    def fake_run_command(
        argv: Sequence[str],
        cwd: Path,
        allowed: Set[str],
    ) -> _CommandResult:
        assert "pyright" in argv[0]
        assert cwd == tmp_path
        assert allowed == {"pyright"}
        return _CommandResult(stdout=json.dumps(payload))

    def fake_warning(
        _msg: str,
        parsed_errors: int,
        parsed_warnings: int,
        parsed_total: int,
        tool_errors: int,
        tool_warnings: int,
        tool_total: int,
        **kwargs: object,
    ) -> None:
        captured_warning["payload"] = (
            parsed_errors,
            parsed_warnings,
            parsed_total,
            tool_errors,
            tool_warnings,
            tool_total,
        )

    monkeypatch.setattr("typewiz.engines.execution.run_command", fake_run_command)
    monkeypatch.setattr("typewiz.engines.execution.logger.warning", fake_warning)
    result = run_pyright(tmp_path, mode=Mode.CURRENT, command=["pyright", "--outputjson"])
    assert len(result.diagnostics) == 1
    diag = result.diagnostics[0]
    assert diag.path == Path("pkg/app.py")
    assert diag.severity is SeverityLevel.ERROR
    assert captured_warning["payload"] == (1, 0, 1, 2, 0, 2)


def test_run_mypy_parses_stdout_and_stderr(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    stdout = "\n".join([
        f"{tmp_path / 'pkg' / 'app.py'}:10:5: error: failure [E001]",
        "invalid line",
        "Success: no issues found",
    ])
    stderr = "config error"

    def fake_run_command(
        argv: Sequence[str],
        cwd: Path,
        allowed: Set[str],
    ) -> _CommandResult:
        assert cwd == tmp_path
        assert argv[0] == "python"
        assert allowed == {argv[0]}
        return _CommandResult(stdout=stdout, stderr=stderr, exit_code=1)

    monkeypatch.setattr("typewiz.engines.execution.run_command", fake_run_command)
    result = run_mypy(tmp_path, mode=Mode.FULL, command=["python", "-m", "mypy"])
    messages = [diag.message for diag in result.diagnostics]
    assert any("config error" in message for message in messages)
    assert any("invalid line" in message for message in messages)
    assert any("failure" in message for message in messages)
