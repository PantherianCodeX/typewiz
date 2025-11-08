# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path

import pytest

from typewiz.config import AuditConfig
from typewiz.core.model_types import Mode
from typewiz.core.type_aliases import EngineName, RelPath
from typewiz.engines.base import EngineContext, EngineOptions
from typewiz.engines.registry import (
    ENTRY_POINT_GROUP,
    EngineDescriptor,
    builtin_engines,
    describe_engines,
    entrypoint_engines,
    resolve_engines,
)


@pytest.fixture(autouse=True)
def clear_engine_caches() -> Generator[None, None, None]:
    entrypoint_engines.cache_clear()
    builtin_engines.cache_clear()
    yield
    entrypoint_engines.cache_clear()
    builtin_engines.cache_clear()


class DummyEngine:
    name = "dummy"

    def run(self, context: EngineContext, paths: list[RelPath]) -> None:  # pragma: no cover
        raise NotImplementedError

    def fingerprint_targets(self, context: EngineContext, paths: list[RelPath]) -> list[str]:
        return []


@dataclass
class _EntryPoint:
    name: str
    group: str
    obj: object

    def load(self) -> object:
        return self.obj


class _EntryPoints:
    def __init__(self, entries: list[_EntryPoint]) -> None:
        super().__init__()
        self._entries = entries

    def select(self, *, group: str) -> list[_EntryPoint]:
        return [entry for entry in self._entries if entry.group == group]


def test_entrypoint_engines_loads_and_validates(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy = DummyEngine()
    entry_points = _EntryPoints([
        _EntryPoint("dummy", ENTRY_POINT_GROUP, dummy),
        _EntryPoint("callable", ENTRY_POINT_GROUP, lambda: DummyEngine()),
    ])

    def fake_metadata_entry_points() -> _EntryPoints:
        return entry_points

    monkeypatch.setattr(
        "typewiz.engines.registry.metadata.entry_points", fake_metadata_entry_points
    )
    engines = entrypoint_engines()
    assert EngineName("dummy") in engines
    assert isinstance(engines[EngineName("dummy")], DummyEngine)


def test_entrypoint_engines_ignores_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    entry_points = _EntryPoints([
        _EntryPoint("invalid", ENTRY_POINT_GROUP, object()),
    ])

    def fake_metadata_entry_points() -> _EntryPoints:
        return entry_points

    monkeypatch.setattr(
        "typewiz.engines.registry.metadata.entry_points", fake_metadata_entry_points
    )
    engines = entrypoint_engines()
    assert engines == {}


def test_describe_engines_reports_builtin(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_entrypoint_engines() -> dict[EngineName, object]:
        return {}

    monkeypatch.setattr("typewiz.engines.registry.entrypoint_engines", fake_entrypoint_engines)
    descriptors = describe_engines()
    assert any(desc.origin == "builtin" for desc in descriptors)
    assert all(isinstance(desc, EngineDescriptor) for desc in descriptors)


def test_resolve_engines_known_and_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_entrypoint_engines() -> dict[EngineName, object]:
        return {}

    monkeypatch.setattr("typewiz.engines.registry.entrypoint_engines", fake_entrypoint_engines)
    engines = resolve_engines([EngineName("pyright")])
    assert len(engines) == 1
    with pytest.raises(ValueError):
        _ = resolve_engines(["missing"])


def test_engine_options_round_trip(tmp_path: Path) -> None:
    options = EngineOptions(
        plugin_args=["--strict"],
        config_file=None,
        include=[RelPath("src")],
        exclude=[],
        profile=None,
    )
    context = EngineContext(
        project_root=tmp_path,
        audit_config=AuditConfig(),
        mode=Mode.CURRENT,
        engine_options=options,
    )
    engine = builtin_engines()[EngineName("pyright")]
    assert engine.fingerprint_targets(context, []) == []
