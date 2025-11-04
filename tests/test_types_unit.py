from __future__ import annotations

from pathlib import Path

from typewiz.types import Diagnostic, RunResult


def _make_diag(code: str | None, severity: str) -> Diagnostic:
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
    unknown = _make_diag("reportUnknownMemberType", "error")
    optional = _make_diag("OptionalMemberAccess", "warning")
    unused = _make_diag("warnUnusedCallResult", "warning")
    general = _make_diag("attr-defined", "error")
    none_code = _make_diag(None, "info")

    assert unknown.category() == "unknown"
    assert optional.category() == "optional"
    assert unused.category() == "unused"
    assert general.category() == "general"
    assert none_code.category() == "general"


def test_run_result_severity_counts() -> None:
    diagnostics = [
        _make_diag("code", "Error"),
        _make_diag("code", "WARNING"),
        _make_diag("code", "warning"),
        _make_diag("code", "INFO"),
    ]
    result = RunResult(
        tool="stub",
        mode="current",
        command=["stub"],
        exit_code=0,
        duration_ms=0.1,
        diagnostics=diagnostics,
    )
    counts = result.severity_counts()
    assert counts["error"] == 1
    assert counts["warning"] == 2
    assert counts["info"] == 1
