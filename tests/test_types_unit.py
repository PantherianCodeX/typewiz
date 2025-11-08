# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

from pathlib import Path

import pytest

from typewiz.core.model_types import (
    DashboardView,
    DataFormat,
    FailOnPolicy,
    HotspotKind,
    LogFormat,
    Mode,
    ReadinessLevel,
    SeverityLevel,
    SignaturePolicy,
    SummaryStyle,
)
from typewiz.core.type_aliases import ToolName
from typewiz.core.types import Diagnostic, RunResult

STUB_TOOL = ToolName("stub")


def _make_diag(code: str | None, severity: SeverityLevel) -> Diagnostic:
    return Diagnostic(
        tool=STUB_TOOL,
        severity=severity,
        path=Path("example.py"),
        line=1,
        column=1,
        code=code,
        message="msg",
    )


def test_run_result_severity_counts() -> None:
    diagnostics = [
        _make_diag("code", SeverityLevel.ERROR),
        _make_diag("code", SeverityLevel.WARNING),
        _make_diag("code", SeverityLevel.WARNING),
        _make_diag("code", SeverityLevel.INFORMATION),
    ]
    result = RunResult(
        tool=STUB_TOOL,
        mode=Mode.CURRENT,
        command=["stub"],
        exit_code=0,
        duration_ms=0.1,
        diagnostics=diagnostics,
    )
    counts = result.severity_counts()
    assert counts[SeverityLevel.ERROR] == 1
    assert counts[SeverityLevel.WARNING] == 2
    assert counts[SeverityLevel.INFORMATION] == 1


def test_model_type_from_str_helpers() -> None:
    assert LogFormat.from_str(" JSON ") is LogFormat.JSON
    assert DataFormat.from_str("table") is DataFormat.TABLE
    assert DashboardView.from_str("READINESS") is DashboardView.READINESS
    assert ReadinessLevel.from_str("Folder") is ReadinessLevel.FOLDER
    assert HotspotKind.from_str("FILES") is HotspotKind.FILES
    assert SummaryStyle.from_str("full") is SummaryStyle.FULL
    assert SignaturePolicy.from_str(" Warn ") is SignaturePolicy.WARN
    assert FailOnPolicy.from_str("ANY") is FailOnPolicy.ANY

    with pytest.raises(ValueError):
        _ = LogFormat.from_str("binary")
    with pytest.raises(ValueError):
        _ = DataFormat.from_str("yaml")
