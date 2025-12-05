# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Unit tests for Misc Aggregate."""

from __future__ import annotations

from pathlib import Path

import pytest

from typewiz.core.model_types import Mode, SeverityLevel
from typewiz.core.type_aliases import ToolName
from typewiz.core.types import Diagnostic, RunResult
from typewiz.manifest.aggregate import summarise_run

pytestmark = pytest.mark.unit

PYRIGHT_TOOL = ToolName("pyright")


def make_diag(
    path: str,
    *,
    severity: SeverityLevel,
    line: int = 1,
    column: int = 1,
    code: str | None = None,
) -> Diagnostic:
    return Diagnostic(
        tool=PYRIGHT_TOOL,
        severity=severity,
        path=Path(path),
        line=line,
        column=column,
        code=code,
        message=f"{severity.value} message",
        raw={},
    )


def test_summarise_run_typed_output() -> None:
    diagnostics = [
        make_diag("pkg/module.py", severity=SeverityLevel.ERROR, code="reportGeneralTypeIssues"),
        make_diag(
            "pkg/module.py",
            severity=SeverityLevel.WARNING,
            code="reportUnknownMemberType",
        ),
        make_diag("pkg/sub/module2.py", severity=SeverityLevel.INFORMATION),
    ]
    run = RunResult(
        tool=PYRIGHT_TOOL,
        mode=Mode.FULL,
        command=["pyright"],
        exit_code=0,
        duration_ms=10.0,
        diagnostics=diagnostics,
    )

    aggregated = summarise_run(run, max_depth=2)
    summary = aggregated["summary"]
    assert "errors" in summary
    assert summary["errors"] == 1
    assert "warnings" in summary
    assert summary["warnings"] == 1
    assert "total" in summary
    assert summary["total"] == 3
    assert "severityBreakdown" in summary
    assert summary["severityBreakdown"][SeverityLevel.ERROR] == 1
    assert any(entry["path"] == "pkg" for entry in aggregated["perFolder"])
    file_entry = aggregated["perFile"][0]
    assert file_entry["diagnostics"][0]["message"].endswith("message")
