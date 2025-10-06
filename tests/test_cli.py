from __future__ import annotations

from pathlib import Path

import pytest

from typing_inspector.cli import main
from typing_inspector.types import Diagnostic, RunResult


@pytest.fixture
def fake_run(tmp_path: Path) -> RunResult:
    diag = Diagnostic(
        tool="pyright",
        severity="error",
        path=tmp_path / "module.py",
        line=1,
        column=1,
        code="reportGeneralTypeIssues",
        message="oops",
        raw={},
    )
    return RunResult(
        tool="pyright",
        mode="current",
        command=["pyright"],
        exit_code=1,
        duration_ms=1.0,
        diagnostics=[diag],
    )


def test_cli_audit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_run: RunResult) -> None:
    outputs = {}

    def fake_pyright(*args, **kwargs):  # type: ignore[no-untyped-def]
        return fake_run

    def fake_mypy(*args, **kwargs):  # type: ignore[no-untyped-def]
        return fake_run

    monkeypatch.setattr("typing_inspector.cli.run_pyright", fake_pyright)
    monkeypatch.setattr("typing_inspector.cli.run_mypy", fake_mypy)

    manifest_path = tmp_path / "manifest.json"
    (tmp_path / "pyrightconfig.json").write_text("{}", encoding="utf-8")
    (tmp_path / "mypy.ini").write_text("[mypy]\n", encoding="utf-8")
    exit_code = main([
        "audit",
        "--project-root",
        str(tmp_path),
        "--full-path",
        "src",
        "--manifest",
        str(manifest_path),
        "--dashboard-markdown",
        str(tmp_path / "dashboard.md"),
        "--fail-on",
        "warnings",
    ])

    assert exit_code == 2  # fail on warnings triggered
    assert manifest_path.exists()
    assert (tmp_path / "dashboard.md").exists()


def test_cli_dashboard_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_run: RunResult) -> None:
    manifest = {
        "generatedAt": "2025-01-01T00:00:00Z",
        "projectRoot": str(tmp_path),
        "runs": [],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(__import__("json").dumps(manifest), encoding="utf-8")

    exit_code = main([
        "dashboard",
        "--manifest",
        str(manifest_path),
        "--format",
        "json",
    ])
    assert exit_code == 0
