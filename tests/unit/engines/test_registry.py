# Copyright 2025 CrownOps Engineering
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Unit tests for Engines Registry."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from ratchetr.config import AuditConfig
from ratchetr.core.model_types import Mode
from ratchetr.core.type_aliases import EngineName, RelPath
from ratchetr.engines.base import EngineContext, EngineOptions
from ratchetr.engines.registry import (
    ENTRY_POINT_GROUP,
    EngineDescriptor,
    builtin_engines,
    describe_engines,
    entrypoint_engines,
    resolve_engines,
)

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

pytestmark = [pytest.mark.unit, pytest.mark.engine]


@pytest.fixture(autouse=True)
def clear_engine_caches() -> Generator[None, None, None]:
    entrypoint_engines.cache_clear()
    builtin_engines.cache_clear()
    yield
    entrypoint_engines.cache_clear()
    builtin_engines.cache_clear()


class DummyEngine:
    """Minimal engine stub used to simulate installed entry points."""

    name = "dummy"
    DEFAULT_FINGERPRINT_TARGETS: tuple[str, ...] = ()

    def run(self, context: EngineContext, paths: list[RelPath]) -> None:  # pragma: no cover
        raise NotImplementedError

    def fingerprint_targets(self, _context: EngineContext, _paths: list[RelPath]) -> list[str]:
        return list(self.DEFAULT_FINGERPRINT_TARGETS)


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

    def _make_dummy_engine() -> DummyEngine:
        return DummyEngine()

    entry_points = _EntryPoints([
        _EntryPoint("dummy", ENTRY_POINT_GROUP, dummy),
        _EntryPoint("callable", ENTRY_POINT_GROUP, _make_dummy_engine),
    ])

    def fake_metadata_entry_points() -> _EntryPoints:
        return entry_points

    monkeypatch.setattr("ratchetr.engines.registry.metadata.entry_points", fake_metadata_entry_points)
    engines = entrypoint_engines()
    assert EngineName("dummy") in engines
    assert isinstance(engines[EngineName("dummy")], DummyEngine)


def test_entrypoint_engines_ignores_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    entry_points = _EntryPoints([
        _EntryPoint("invalid", ENTRY_POINT_GROUP, object()),
    ])

    def fake_metadata_entry_points() -> _EntryPoints:
        return entry_points

    monkeypatch.setattr("ratchetr.engines.registry.metadata.entry_points", fake_metadata_entry_points)
    engines = entrypoint_engines()
    assert engines == {}


def test_describe_engines_reports_builtin(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_entrypoint_engines() -> dict[EngineName, object]:
        return {}

    monkeypatch.setattr("ratchetr.engines.registry.entrypoint_engines", fake_entrypoint_engines)
    descriptors = describe_engines()
    assert any(desc.origin == "builtin" for desc in descriptors)
    assert all(isinstance(desc, EngineDescriptor) for desc in descriptors)


def test_resolve_engines_known_and_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_entrypoint_engines() -> dict[EngineName, object]:
        return {}

    monkeypatch.setattr("ratchetr.engines.registry.entrypoint_engines", fake_entrypoint_engines)
    engines = resolve_engines([EngineName("pyright")])
    assert len(engines) == 1
    with pytest.raises(ValueError, match="Unknown engine 'missing'"):
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
