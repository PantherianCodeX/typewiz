# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from typewiz.api import run_audit
from typewiz.config import AuditConfig, Config, EngineSettings
from typewiz.engines.base import EngineContext, EngineResult
from typewiz.model_types import Mode
from typewiz.type_aliases import EngineName, RunnerName, ToolName
from typewiz.utils import consume


class RecordingEngine:
    name = "stub"

    def __init__(self) -> None:
        super().__init__()
        self.invocations: list[Mode] = []

    def run(self, context: EngineContext, paths: list[str]) -> EngineResult:
        self.invocations.append(context.mode)
        return EngineResult(
            engine=ToolName(self.name),
            mode=context.mode,
            command=["stub", str(context.mode)],
            exit_code=0,
            duration_ms=0.1,
            diagnostics=[],
        )

    def category_mapping(self) -> dict[str, list[str]]:
        return {}

    def fingerprint_targets(self, context: EngineContext, paths: list[str]) -> list[str]:
        return []


def _patch_engine_resolution(monkeypatch: pytest.MonkeyPatch, engine: RecordingEngine) -> None:
    def _resolve(_: Sequence[str]) -> list[RecordingEngine]:
        return [engine]

    monkeypatch.setattr("typewiz.engines.resolve_engines", _resolve)
    monkeypatch.setattr("typewiz.api.resolve_engines", _resolve)


def _prepare_workspace(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    consume((tmp_path / "src" / "mod.py").write_text("x = 1\n", encoding="utf-8"))


def test_cache_invalidation_on_tool_version_change(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    engine = RecordingEngine()
    _patch_engine_resolution(monkeypatch, engine)
    _prepare_workspace(tmp_path)

    # First run with version 1.0
    def _versions_v1(_: Sequence[str]) -> dict[str, str]:
        return {"stub": "1.0"}

    monkeypatch.setattr("typewiz.api.detect_tool_versions", _versions_v1)
    override = AuditConfig(full_paths=["src"], runners=[STUB_RUNNER])
    consume(run_audit(project_root=tmp_path, override=override))
    assert engine.invocations.count(Mode.FULL) == 1

    # Second run with version 2.0 should bypass cache
    def _versions_v2(_: Sequence[str]) -> dict[str, str]:
        return {"stub": "2.0"}

    monkeypatch.setattr("typewiz.api.detect_tool_versions", _versions_v2)
    consume(run_audit(project_root=tmp_path, override=override))
    assert engine.invocations.count(Mode.FULL) == 2


def test_cache_invalidation_on_config_change(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    engine = RecordingEngine()
    _patch_engine_resolution(monkeypatch, engine)
    _prepare_workspace(tmp_path)

    cfg_file = tmp_path / "stub.cfg"
    consume(cfg_file.write_text("a=1\n", encoding="utf-8"))

    settings = EngineSettings(config_file=cfg_file)
    config = Config(
        audit=AuditConfig(
            full_paths=["src"],
            runners=[STUB_RUNNER],
            engine_settings={STUB: settings},
        ),
    )

    consume(run_audit(project_root=tmp_path, config=config))
    assert engine.invocations.count(Mode.FULL) == 1

    # Modify config; cache key should change
    consume(cfg_file.write_text("a=2\n", encoding="utf-8"))
    consume(run_audit(project_root=tmp_path, config=config))
    assert engine.invocations.count(Mode.FULL) == 2


def test_cache_invalidation_on_plugin_args_change(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    engine = RecordingEngine()
    _patch_engine_resolution(monkeypatch, engine)
    _prepare_workspace(tmp_path)

    base = AuditConfig(full_paths=["src"], runners=[STUB_RUNNER])
    consume(run_audit(project_root=tmp_path, override=base))
    assert engine.invocations.count(Mode.FULL) == 1

    # Add a plugin arg which participates in the cache key; expect a miss
    override = AuditConfig(
        full_paths=["src"],
        runners=[STUB_RUNNER],
        plugin_args={STUB: ["--flag"]},
    )
    consume(run_audit(project_root=tmp_path, override=override))
    assert engine.invocations.count(Mode.FULL) == 2


STUB = EngineName("stub")
STUB_RUNNER = RunnerName(STUB)
