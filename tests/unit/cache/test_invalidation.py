# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Unit tests for Cache Invalidation."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from tests.fixtures.stubs import RecordingEngine
from typewiz._internal.utils import consume
from typewiz.api import run_audit
from typewiz.config import AuditConfig, Config, EngineSettings
from typewiz.core.model_types import Mode
from typewiz.core.type_aliases import EngineName, RunnerName

pytestmark = pytest.mark.unit


def _patch_engine_resolution(monkeypatch: pytest.MonkeyPatch, engine: RecordingEngine) -> None:
    def _resolve(_: Sequence[str]) -> list[RecordingEngine]:
        return [engine]

    monkeypatch.setattr("typewiz.engines.resolve_engines", _resolve)
    monkeypatch.setattr("typewiz.audit.api.resolve_engines", _resolve)


def _prepare_workspace(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    consume((tmp_path / "src" / "mod.py").write_text("x = 1\n", encoding="utf-8"))


def _full_invocation_count(engine: RecordingEngine) -> int:
    return sum(1 for invocation in engine.invocations if invocation.mode is Mode.FULL)


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

    monkeypatch.setattr("typewiz.audit.api.detect_tool_versions", _versions_v1)
    override = AuditConfig(full_paths=["src"], runners=[STUB_RUNNER])
    consume(run_audit(project_root=tmp_path, override=override))
    assert _full_invocation_count(engine) == 1

    # Second run with version 2.0 should bypass cache
    def _versions_v2(_: Sequence[str]) -> dict[str, str]:
        return {"stub": "2.0"}

    monkeypatch.setattr("typewiz.audit.api.detect_tool_versions", _versions_v2)
    consume(run_audit(project_root=tmp_path, override=override))
    assert _full_invocation_count(engine) == 2


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
    assert _full_invocation_count(engine) == 1

    # Modify config; cache key should change
    consume(cfg_file.write_text("a=2\n", encoding="utf-8"))
    consume(run_audit(project_root=tmp_path, config=config))
    assert _full_invocation_count(engine) == 2


def test_cache_invalidation_on_plugin_args_change(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    engine = RecordingEngine()
    _patch_engine_resolution(monkeypatch, engine)
    _prepare_workspace(tmp_path)

    base = AuditConfig(full_paths=["src"], runners=[STUB_RUNNER])
    consume(run_audit(project_root=tmp_path, override=base))
    assert _full_invocation_count(engine) == 1

    # Add a plugin arg which participates in the cache key; expect a miss
    override = AuditConfig(
        full_paths=["src"],
        runners=[STUB_RUNNER],
        plugin_args={STUB: ["--flag"]},
    )
    consume(run_audit(project_root=tmp_path, override=override))
    assert _full_invocation_count(engine) == 2


STUB = EngineName("stub")
STUB_RUNNER = RunnerName(STUB)
