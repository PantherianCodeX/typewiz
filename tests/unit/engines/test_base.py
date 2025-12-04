# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

from __future__ import annotations

from pathlib import Path

import pytest

from typewiz.core.model_types import Mode, SeverityLevel
from typewiz.core.type_aliases import ToolName
from typewiz.core.types import Diagnostic
from typewiz.engines.base import EngineResult

pytestmark = [pytest.mark.unit, pytest.mark.engine]


class _StubLogger:
    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def warning(self, message: str, *args: object, **_: object) -> None:
        formatted = message % args if args else message
        self.messages.append(formatted)


def _make_diagnostic() -> Diagnostic:
    return Diagnostic(
        tool=ToolName("pyright"),
        severity=SeverityLevel.ERROR,
        path=Path("src/app.py"),
        line=1,
        column=1,
        code="E001",
        message="boom",
        raw={},
    )


def test_engine_result_warns_for_empty_command(monkeypatch: pytest.MonkeyPatch) -> None:
    stub_logger = _StubLogger()
    monkeypatch.setattr("typewiz.engines.base.logger", stub_logger)
    _ = EngineResult(
        engine=ToolName("pyright"),
        mode=Mode.CURRENT,
        command=[],
        exit_code=0,
        duration_ms=1.0,
        diagnostics=[_make_diagnostic()],
    )
    assert any("empty command" in message for message in stub_logger.messages)


def test_engine_result_warns_for_negative_duration(monkeypatch: pytest.MonkeyPatch) -> None:
    stub_logger = _StubLogger()
    monkeypatch.setattr("typewiz.engines.base.logger", stub_logger)
    _ = EngineResult(
        engine=ToolName("pyright"),
        mode=Mode.CURRENT,
        command=["pyright"],
        exit_code=0,
        duration_ms=-1.0,
        diagnostics=[_make_diagnostic()],
    )
    assert any("negative duration" in message for message in stub_logger.messages)


def test_engine_result_warns_for_negative_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    stub_logger = _StubLogger()
    monkeypatch.setattr("typewiz.engines.base.logger", stub_logger)
    _ = EngineResult(
        engine=ToolName("pyright"),
        mode=Mode.CURRENT,
        command=["pyright"],
        exit_code=-5,
        duration_ms=0.1,
        diagnostics=[_make_diagnostic()],
    )
    assert any("negative exit code" in message for message in stub_logger.messages)
