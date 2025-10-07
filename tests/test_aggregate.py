from __future__ import annotations

from pathlib import Path

from typewiz.aggregate import summarise_run
from typewiz.types import Diagnostic, RunResult


def make_diag(
    path: str, *, severity: str, line: int = 1, column: int = 1, code: str | None = None
) -> Diagnostic:
    return Diagnostic(
        tool="pyright",
        severity=severity,
        path=Path(path),
        line=line,
        column=column,
        code=code,
        message=f"{severity} message",
        raw={},
    )


def test_summarise_run_typed_output() -> None:
    diagnostics = [
        make_diag("pkg/module.py", severity="error", code="reportGeneralTypeIssues"),
        make_diag("pkg/module.py", severity="warning", code="reportUnknownMemberType"),
        make_diag("pkg/sub/module2.py", severity="information"),
    ]
    run = RunResult(
        tool="pyright",
        mode="full",
        command=["pyright"],
        exit_code=0,
        duration_ms=10.0,
        diagnostics=diagnostics,
    )

    aggregated = summarise_run(run, max_depth=2)
    assert aggregated["summary"]["errors"] == 1
    assert aggregated["summary"]["warnings"] == 1
    assert aggregated["summary"]["total"] == 3
    assert aggregated["summary"]["severityBreakdown"]["error"] == 1
    assert any(entry["path"] == "pkg" for entry in aggregated["perFolder"])
    file_entry = aggregated["perFile"][0]
    assert file_entry["diagnostics"][0]["message"].endswith("message")
