# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

from pathlib import Path

import pytest

from typewiz.model_types import (
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
from typewiz.types import Diagnostic, RunResult


def _make_diag(code: str | None, severity: SeverityLevel) -> Diagnostic:
    return Diagnostic(
        tool="stub",
        severity=severity,
        path=Path("example.py"),
        line=1,
        column=1,
        code=code,
        message="msg",
    )


def test_diagnostic_category_branches() -> None:
    unknown = _make_diag("reportUnknownMemberType", SeverityLevel.ERROR)
    optional = _make_diag("OptionalMemberAccess", SeverityLevel.WARNING)
    unused = _make_diag("warnUnusedCallResult", SeverityLevel.WARNING)
    general = _make_diag("attr-defined", SeverityLevel.ERROR)
    none_code = _make_diag(None, SeverityLevel.INFORMATION)

    assert unknown.category() == "unknown"
    assert optional.category() == "optional"
    assert unused.category() == "unused"
    assert general.category() == "general"
    assert none_code.category() == "general"


def test_run_result_severity_counts() -> None:
    diagnostics = [
        _make_diag("code", SeverityLevel.ERROR),
        _make_diag("code", SeverityLevel.WARNING),
        _make_diag("code", SeverityLevel.WARNING),
        _make_diag("code", SeverityLevel.INFORMATION),
    ]
    result = RunResult(
        tool="stub",
        mode=Mode.CURRENT,
        command=["stub"],
        exit_code=0,
        duration_ms=0.1,
        diagnostics=diagnostics,
    )
    counts = result.severity_counts()
    assert counts["error"] == 1
    assert counts["warning"] == 2
    assert counts["information"] == 1


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
