from __future__ import annotations

from pathlib import Path

import pytest

from pytc import AuditConfig, run_audit
from pytc.plugins.base import PluginCommand, PluginContext
from pytc.types import Diagnostic, RunResult


class StubRunner:
    def __init__(self, result: RunResult) -> None:
        self.name = "stub"
        self._result = result

    def generate_commands(self, context: PluginContext) -> list[PluginCommand]:
        return [PluginCommand(self.name, "full", ["stub"])]

    def execute(self, context: PluginContext, command: PluginCommand) -> RunResult:
        return self._result


@pytest.fixture
def fake_run_result(tmp_path: Path) -> RunResult:
    (tmp_path / "pkg").mkdir(exist_ok=True)
    diagnostics = [
        Diagnostic(
            tool="stub",
            severity="error",
            path=tmp_path / "pkg" / "module.py",
            line=1,
            column=1,
            code="reportGeneralTypeIssues",
            message="problem",
            raw={},
        )
    ]
    return RunResult(
        tool="stub",
        mode="full",
        command=["stub"],
        exit_code=1,
        duration_ms=5.0,
        diagnostics=diagnostics,
    )


def test_run_audit_programmatic(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, fake_run_result: RunResult) -> None:
    monkeypatch.setattr("pytc.plugins.resolve_runners", lambda names: [StubRunner(fake_run_result)])
    monkeypatch.setattr("pytc.api.resolve_runners", lambda names: [StubRunner(fake_run_result)])

    (tmp_path / "pkg").mkdir(parents=True, exist_ok=True)
    (tmp_path / "pyrightconfig.json").write_text("{}", encoding="utf-8")
    override = AuditConfig(full_paths=["src"], dashboard_json=tmp_path / "summary.json", runners=["stub"])

    result = run_audit(project_root=tmp_path, override=override, full_paths=["src"], build_summary_output=True)

    assert result.summary is not None
    assert result.summary["topFolders"]
    assert result.error_count == 1
    assert (tmp_path / "summary.json").exists()
