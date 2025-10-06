from __future__ import annotations

from pathlib import Path

import pytest

from typing_inspector import AuditConfig, run_audit
from typing_inspector.types import Diagnostic, RunResult


@pytest.fixture
def fake_run_result(tmp_path: Path) -> RunResult:
    diagnostics = [
        Diagnostic(
            tool="pyright",
            severity="error",
            path=tmp_path / "module.py",
            line=1,
            column=1,
            code="reportGeneralTypeIssues",
            message="problem",
            raw={},
        )
    ]
    return RunResult(
        tool="pyright",
        mode="current",
        command=["pyright"],
        exit_code=1,
        duration_ms=5.0,
        diagnostics=diagnostics,
    )


def test_run_audit_programmatic(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_run_result: RunResult) -> None:
    def fake_pyright(*args, **kwargs):  # type: ignore[no-untyped-def]
        return fake_run_result

    def fake_mypy(*args, **kwargs):  # type: ignore[no-untyped-def]
        return fake_run_result

    monkeypatch.setattr("typing_inspector.api.run_pyright", fake_pyright)
    monkeypatch.setattr("typing_inspector.api.run_mypy", fake_mypy)

    override = AuditConfig(full_paths=["src"], dashboard_json=tmp_path / "summary.json")
    (tmp_path / "pyrightconfig.json").write_text("{}", encoding="utf-8")
    (tmp_path / "mypy.ini").write_text("[mypy]\n", encoding="utf-8")
    result = run_audit(project_root=tmp_path, full_paths=["src"], override=override, build_summary_output=True)

    assert result.summary is not None
    assert result.summary["topFolders"]
    assert (tmp_path / "summary.json").exists()
