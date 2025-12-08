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

"""Unit tests for Engines Base."""

from __future__ import annotations

from pathlib import Path

import pytest

from ratchetr.core.model_types import Mode, SeverityLevel
from ratchetr.core.type_aliases import ToolName
from ratchetr.core.types import Diagnostic
from ratchetr.engines.base import EngineResult

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
    monkeypatch.setattr("ratchetr.engines.base.logger", stub_logger)
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
    monkeypatch.setattr("ratchetr.engines.base.logger", stub_logger)
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
    monkeypatch.setattr("ratchetr.engines.base.logger", stub_logger)
    _ = EngineResult(
        engine=ToolName("pyright"),
        mode=Mode.CURRENT,
        command=["pyright"],
        exit_code=-5,
        duration_ms=0.1,
        diagnostics=[_make_diagnostic()],
    )
    assert any("negative exit code" in message for message in stub_logger.messages)
