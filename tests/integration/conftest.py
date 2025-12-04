# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Fixtures for multi-component integration tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from typewiz.core.model_types import Mode, SeverityLevel
from typewiz.core.type_aliases import ToolName
from typewiz.core.types import Diagnostic, RunResult

STUB_TOOL = ToolName("stub")


@pytest.fixture
def fake_run(tmp_path: Path) -> RunResult:
    """Provide a representative run payload for CLI->engine workflows."""
    (tmp_path / "pkg").mkdir(exist_ok=True)
    diag = Diagnostic(
        tool=STUB_TOOL,
        severity=SeverityLevel.ERROR,
        path=tmp_path / "pkg" / "module.py",
        line=1,
        column=1,
        code="reportGeneralTypeIssues",
        message="oops",
        raw={},
    )
    return RunResult(
        tool=STUB_TOOL,
        mode=Mode.CURRENT,
        command=["stub"],
        exit_code=1,
        duration_ms=1.0,
        diagnostics=[diag],
    )
