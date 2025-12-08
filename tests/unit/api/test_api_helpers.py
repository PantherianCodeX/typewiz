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

"""Unit tests for API Helpers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from ratchetr._internal.utils import consume
from ratchetr.audit.execution import apply_engine_paths, resolve_engine_options
from ratchetr.audit.options import merge_engine_settings_map
from ratchetr.audit.paths import (
    fingerprint_targets,
    normalise_override_entries,
    normalise_paths,
    relative_override_path,
)
from ratchetr.compat.python import override
from ratchetr.config import AuditConfig, EngineProfile, EngineSettings, PathOverride
from ratchetr.core.type_aliases import EngineName, ProfileName, RelPath
from ratchetr.engines.base import BaseEngine, EngineContext, EngineResult

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ratchetr.core.model_types import CategoryMapping

pytestmark = pytest.mark.unit


def test_merge_engine_settings_map_merges_profiles() -> None:
    stub = EngineName("stub")
    aux = EngineName("aux")
    strict_profile = ProfileName("strict")
    lenient_profile = ProfileName("lenient")
    base_settings = {
        stub: EngineSettings(
            plugin_args=["--base"],
            include=["src"],
            exclude=["legacy"],
            profiles={strict_profile: EngineProfile(plugin_args=["--strict"])},
        ),
    }
    override_settings = {
        stub: EngineSettings(
            plugin_args=["--override"],
            include=["extras"],
            exclude=[],
            default_profile=strict_profile,
            profiles={
                strict_profile: EngineProfile(plugin_args=["--stricter"], exclude=["legacy"]),
                lenient_profile: EngineProfile(plugin_args=["--lenient"]),
            },
        ),
        aux: EngineSettings(plugin_args=["--aux"]),
    }

    merged = merge_engine_settings_map(base_settings, override_settings)
    assert merged[stub].plugin_args == ["--base", "--override"]
    assert merged[stub].include == ["src", "extras"]
    assert merged[stub].default_profile == strict_profile
    assert merged[stub].profiles[strict_profile].plugin_args == ["--strict", "--stricter"]
    assert lenient_profile in merged[stub].profiles
    assert merged[aux].plugin_args == ["--aux"]


def test_normalise_paths_handles_duplicates(tmp_path: Path) -> None:
    project_root = tmp_path
    (tmp_path / "src").mkdir()
    paths = ["src", "src/", str(tmp_path / "outside")]
    normalised = normalise_paths(project_root, paths)
    assert normalised[0].endswith("src")
    assert "outside" in normalised
    assert len(normalised) == 2


def test_fingerprint_targets_dedupe(tmp_path: Path) -> None:
    consume(
        (tmp_path / "pyproject.toml").write_text("[project]\nname='demo'\n", encoding="utf-8"),
    )
    targets = fingerprint_targets(
        tmp_path,
        mode_paths=["src"],
        default_paths=["pkg"],
        extra=["src"],
    )
    assert targets[0] == "src"
    assert "pyproject.toml" in targets
    assert len(targets) == len(set(targets))


def test_normalise_override_entries_defaults(tmp_path: Path) -> None:
    override_path = tmp_path / "pkg"
    override_path.mkdir(parents=True)
    entries = normalise_override_entries(tmp_path, override_path, [])
    assert entries == [RelPath("pkg")]


def test_relative_override_path_outside_root(tmp_path: Path) -> None:
    outside = (tmp_path / "..").resolve()
    result = relative_override_path(tmp_path, outside)
    expected = RelPath(Path(os.path.relpath(outside, tmp_path)).as_posix())
    assert result == expected


def test_apply_engine_paths_respects_exclude() -> None:
    result = apply_engine_paths(
        [RelPath("src")],
        [RelPath("pkg"), RelPath("tests")],
        [RelPath("src/tests")],
    )
    assert "src" in result
    assert "pkg" in result
    assert "tests" in result
    assert all(not path.startswith("src/tests") for path in result)


class MinimalEngine(BaseEngine):
    """Minimal BaseEngine implementation used for option resolution tests."""

    name = "stub"

    @override
    def run(self, context: EngineContext, paths: Sequence[RelPath]) -> EngineResult:  # pragma: no cover
        raise NotImplementedError

    @override
    def fingerprint_targets(self, context: EngineContext, paths: Sequence[RelPath]) -> list[str]:
        return []

    @staticmethod
    @override
    def category_mapping() -> CategoryMapping:
        return {"unknownChecks": ["reportGeneralTypeIssues"]}


def test_resolve_engine_options_with_overrides(tmp_path: Path) -> None:
    strict_profile = ProfileName("strict")
    lenient_profile = ProfileName("lenient")
    engine_config = EngineSettings(
        plugin_args=["--engine"],
        include=["pkg"],
        exclude=["legacy"],
        default_profile=strict_profile,
        profiles={
            strict_profile: EngineProfile(
                plugin_args=["--strict"],
                include=["pkg/strict"],
                exclude=[],
            ),
            lenient_profile: EngineProfile(plugin_args=["--lenient"]),
        },
    )
    override_settings = EngineSettings(
        plugin_args=["--override"],
        include=["pkg/override"],
        profiles={
            strict_profile: EngineProfile(
                plugin_args=["--override-strict"],
                include=["pkg/override/strict"],
            ),
        },
        default_profile=strict_profile,
    )
    override = PathOverride(
        path=tmp_path / "pkg",
        engine_settings={EngineName("stub"): override_settings},
        active_profiles={EngineName("stub"): lenient_profile},
    )
    (tmp_path / "pkg").mkdir(parents=True, exist_ok=True)
    (tmp_path / "pkg/override/strict").mkdir(parents=True, exist_ok=True)
    (tmp_path / "pkg/strict").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src").mkdir(exist_ok=True)
    audit_config = AuditConfig(
        plugin_args={EngineName("stub"): ["--base"]},
        engine_settings={EngineName("stub"): engine_config},
        path_overrides=[override],
        active_profiles={EngineName("stub"): lenient_profile},
        full_paths=["src"],
    )

    engine_options = resolve_engine_options(tmp_path, audit_config, MinimalEngine())
    assert engine_options.plugin_args[:2] == ["--base", "--engine"]
    assert any(arg == "--override" for arg in engine_options.plugin_args)
    assert engine_options.profile == strict_profile
    assert engine_options.category_mapping["unknownChecks"] == ["reportGeneralTypeIssues"]
    assert engine_options.overrides
