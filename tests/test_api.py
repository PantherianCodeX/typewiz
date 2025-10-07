from __future__ import annotations

from pathlib import Path
from typing import Sequence

import pytest

from typewiz import AuditConfig, Config, run_audit
from typewiz.config import EngineProfile, EngineSettings
from typewiz.engines.base import EngineContext, EngineResult
from typewiz.types import Diagnostic, RunResult


class StubEngine:
    def __init__(self, result: RunResult) -> None:
        self.name = "stub"
        self._result = result

    def run(self, context: EngineContext, paths: Sequence[str]) -> EngineResult:
        if context.mode == "current":
            return EngineResult(
                engine=self.name,
                mode=context.mode,
                command=["stub", "current"],
                exit_code=0,
                duration_ms=0.1,
                diagnostics=[],
            )
        return EngineResult(
            engine=self.name,
            mode=context.mode,
            command=list(self._result.command),
            exit_code=self._result.exit_code,
            duration_ms=self._result.duration_ms,
            diagnostics=list(self._result.diagnostics),
        )


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
    monkeypatch.setattr("typewiz.engines.resolve_engines", lambda names: [StubEngine(fake_run_result)])
    monkeypatch.setattr("typewiz.api.resolve_engines", lambda names: [StubEngine(fake_run_result)])

    (tmp_path / "pkg").mkdir(parents=True, exist_ok=True)
    (tmp_path / "pyrightconfig.json").write_text("{}", encoding="utf-8")
    override = AuditConfig(full_paths=["src"], dashboard_json=tmp_path / "summary.json", runners=["stub"])

    result = run_audit(project_root=tmp_path, override=override, full_paths=["src"], build_summary_output=True)

    assert result.summary is not None
    assert result.summary["topFolders"]
    assert result.error_count == 1
    assert (tmp_path / "summary.json").exists()


def test_run_audit_applies_engine_profiles(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class RecordingEngine:
        name = "stub"

        def __init__(self) -> None:
            self.invocations: list[tuple[str, list[str], list[str], str | None]] = []

        def run(self, context: EngineContext, paths: Sequence[str]) -> EngineResult:
            self.invocations.append(
                (
                    context.mode,
                    list(context.engine_options.plugin_args),
                    list(paths),
                    context.engine_options.profile,
                )
            )
            return EngineResult(
                engine=self.name,
                mode=context.mode,
                command=["stub", context.mode],
                exit_code=0,
                duration_ms=0.1,
                diagnostics=[],
            )

    engine = RecordingEngine()
    monkeypatch.setattr("typewiz.engines.resolve_engines", lambda names: [engine])
    monkeypatch.setattr("typewiz.api.resolve_engines", lambda names: [engine])

    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "extra").mkdir(parents=True, exist_ok=True)
    (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8")

    profile = EngineProfile(plugin_args=["--strict"], include=["extra"], exclude=[])
    settings = EngineSettings(plugin_args=["--engine"], profiles={"strict": profile})
    config = Config(
        audit=AuditConfig(
            full_paths=["src"],
            plugin_args={"stub": ["--base"]},
            engine_settings={"stub": settings},
            active_profiles={"stub": "strict"},
            runners=["stub"],
        )
    )

    result = run_audit(project_root=tmp_path, config=config, build_summary_output=False)

    assert len(engine.invocations) == 2
    modes = {mode for mode, _, _, _ in engine.invocations}
    assert modes == {"current", "full"}
    full_invocation = next(entry for entry in engine.invocations if entry[0] == "full")
    _, args, paths, profile_name = full_invocation
    assert args == ["--base", "--engine", "--strict"]
    assert sorted(paths) == ["extra", "src"]
    assert profile_name == "strict"

    assert {run.profile for run in result.runs} == {"strict"}
    assert all(run.plugin_args == ["--base", "--engine", "--strict"] for run in result.runs)
    assert all(run.include == ["extra"] for run in result.runs)
    run_payload = result.manifest["runs"][0]
    assert run_payload["engineOptions"]["profile"] == "strict"
    assert run_payload["engineOptions"]["include"] == ["extra"]
