from __future__ import annotations

from pathlib import Path
import json

import pytest

from pytc.cli import main
from pytc.plugins.base import PluginCommand, PluginContext
from pytc.types import Diagnostic, RunResult


class StubRunner:
    def __init__(self, result: RunResult) -> None:
        self.name = "stub"
        self._result = result

    def generate_commands(self, context: PluginContext) -> list[PluginCommand]:
        return [PluginCommand(self.name, "current", ["stub"])]

    def execute(self, context: PluginContext, command: PluginCommand) -> RunResult:
        return self._result


@pytest.fixture
def fake_run(tmp_path: Path) -> RunResult:
    (tmp_path / "pkg").mkdir(exist_ok=True)
    diag = Diagnostic(
        tool="stub",
        severity="error",
        path=tmp_path / "pkg" / "module.py",
        line=1,
        column=1,
        code="reportGeneralTypeIssues",
        message="oops",
        raw={},
    )
    return RunResult(
        tool="stub",
        mode="current",
        command=["stub"],
        exit_code=1,
        duration_ms=1.0,
        diagnostics=[diag],
    )


def test_cli_audit(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_run: RunResult) -> None:
    monkeypatch.setattr("pytc.plugins.resolve_runners", lambda names: [StubRunner(fake_run)])
    monkeypatch.setattr("pytc.api.resolve_runners", lambda names: [StubRunner(fake_run)])

    (tmp_path / "pkg").mkdir(exist_ok=True)
    (tmp_path / "pyrightconfig.json").write_text("{}", encoding="utf-8")

    manifest_path = tmp_path / "manifest.json"
    exit_code = main([
        "audit",
        "--runner",
        "stub",
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

    assert exit_code == 2  # fail on warnings triggered (error counts)
    assert manifest_path.exists()
    assert (tmp_path / "dashboard.md").exists()


def test_cli_dashboard_output(tmp_path: Path) -> None:
    manifest = {
        "generatedAt": "2025-01-01T00:00:00Z",
        "projectRoot": str(tmp_path),
        "runs": [],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    exit_code = main([
        "dashboard",
        "--manifest",
        str(manifest_path),
        "--format",
        "json",
    ])
    assert exit_code == 0
