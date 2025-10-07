from __future__ import annotations

from pathlib import Path

import pytest

from typewiz.api import run_audit
from typewiz.config import AuditConfig, Config, EngineSettings
from typewiz.engines.base import EngineContext, EngineResult


class RecordingEngine:
    name = "stub"

    def __init__(self) -> None:
        self.invocations: list[str] = []

    def run(self, context: EngineContext, paths: list[str]) -> EngineResult:
        self.invocations.append(context.mode)
        return EngineResult(
            engine=self.name,
            mode=context.mode,
            command=["stub", context.mode],
            exit_code=0,
            duration_ms=0.1,
            diagnostics=[],
        )

    def category_mapping(self) -> dict[str, list[str]]:
        return {}

    def fingerprint_targets(self, context: EngineContext, paths: list[str]) -> list[str]:
        return []


def _prepare_workspace(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "mod.py").write_text("x = 1\n", encoding="utf-8")


def test_cache_invalidation_on_tool_version_change(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    engine = RecordingEngine()
    monkeypatch.setattr("typewiz.engines.resolve_engines", lambda names: [engine])
    monkeypatch.setattr("typewiz.api.resolve_engines", lambda names: [engine])
    _prepare_workspace(tmp_path)

    # First run with version 1.0
    monkeypatch.setattr("typewiz.api.detect_tool_versions", lambda names: {"stub": "1.0"})
    override = AuditConfig(full_paths=["src"], runners=["stub"])
    run_audit(project_root=tmp_path, override=override)
    assert engine.invocations.count("full") == 1

    # Second run with version 2.0 should bypass cache
    monkeypatch.setattr("typewiz.api.detect_tool_versions", lambda names: {"stub": "2.0"})
    run_audit(project_root=tmp_path, override=override)
    assert engine.invocations.count("full") == 2


def test_cache_invalidation_on_config_change(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    engine = RecordingEngine()
    monkeypatch.setattr("typewiz.engines.resolve_engines", lambda names: [engine])
    monkeypatch.setattr("typewiz.api.resolve_engines", lambda names: [engine])
    _prepare_workspace(tmp_path)

    cfg_file = tmp_path / "stub.cfg"
    cfg_file.write_text("a=1\n", encoding="utf-8")

    settings = EngineSettings(config_file=cfg_file)
    config = Config(audit=AuditConfig(full_paths=["src"], runners=["stub"], engine_settings={"stub": settings}))

    run_audit(project_root=tmp_path, config=config)
    assert engine.invocations.count("full") == 1

    # Modify config; cache key should change
    cfg_file.write_text("a=2\n", encoding="utf-8")
    run_audit(project_root=tmp_path, config=config)
    assert engine.invocations.count("full") == 2


def test_cache_invalidation_on_plugin_args_change(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    engine = RecordingEngine()
    monkeypatch.setattr("typewiz.engines.resolve_engines", lambda names: [engine])
    monkeypatch.setattr("typewiz.api.resolve_engines", lambda names: [engine])
    _prepare_workspace(tmp_path)

    base = AuditConfig(full_paths=["src"], runners=["stub"])
    run_audit(project_root=tmp_path, override=base)
    assert engine.invocations.count("full") == 1

    # Add a plugin arg which participates in the cache key; expect a miss
    override = AuditConfig(full_paths=["src"], runners=["stub"], plugin_args={"stub": ["--flag"]})
    run_audit(project_root=tmp_path, override=override)
    assert engine.invocations.count("full") == 2

