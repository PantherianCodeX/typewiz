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

"""Property-based tests for ratchetr.paths."""

from __future__ import annotations

from pathlib import Path

import hypothesis.strategies as st
import pytest
from hypothesis import HealthCheck, given, settings

from ratchetr.config import PathsConfig
from ratchetr.paths import (
    MANIFEST_CANDIDATE_NAMES,
    EnvOverrides,
    ManifestDiscoveryError,
    PathOverrides,
    ResolvedPaths,
    discover_manifest,
    resolve_paths,
)

pytestmark = pytest.mark.property


def _relative_paths() -> st.SearchStrategy[Path]:
    alphabet = tuple("abcdefghijklmnopqrstuvwxyz0123456789")
    segment = (
        st.lists(st.sampled_from(alphabet), min_size=1, max_size=6)
        .map("".join)
        .filter(lambda value: value not in {".", ".."})
    )
    return st.lists(segment, min_size=1, max_size=3).map(lambda parts: Path("/".join(parts)))


def _ambiguous_candidate_names() -> st.SearchStrategy[list[str]]:
    return st.lists(st.sampled_from(MANIFEST_CANDIDATE_NAMES), min_size=2, max_size=3).filter(
        lambda entries: len(set(entries)) >= 2
    )


def _resolved_paths(repo_root: Path) -> ResolvedPaths:
    home = repo_root / ".ratchetr"
    return ResolvedPaths(
        repo_root=repo_root,
        tool_home=home,
        cache_dir=home / ".cache",
        log_dir=home / "logs",
        manifest_path=home / "manifest.json",
        dashboard_path=home / "dashboard.html",
        config_path=None,
    )


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(cli_manifest=_relative_paths())
def test_h_cli_manifest_override_wins(cli_manifest: Path, tmp_path: Path) -> None:
    repo_root = tmp_path
    overrides = PathOverrides(repo_root=repo_root, manifest_path=cli_manifest)
    env = EnvOverrides(
        config_path=None,
        repo_root=None,
        tool_home=None,
        manifest_path=repo_root / "env-manifest.json",
        cache_dir=None,
        log_dir=None,
        default_paths=None,
    )

    resolved = resolve_paths(
        cli_overrides=overrides,
        env_overrides=env,
        config_paths=PathsConfig(ratchetr_dir=repo_root / "config-home"),
        cwd=repo_root,
    )

    assert resolved.manifest_path == (repo_root / cli_manifest).resolve()


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(cli_tool_home=_relative_paths())
def test_h_cli_tool_home_override_wins(cli_tool_home: Path, tmp_path: Path) -> None:
    repo_root = tmp_path
    overrides = PathOverrides(repo_root=repo_root, tool_home=cli_tool_home)
    env = EnvOverrides(
        config_path=None,
        repo_root=repo_root / "env-root",
        tool_home=repo_root / "env-home",
        manifest_path=None,
        cache_dir=None,
        log_dir=None,
        default_paths=None,
    )
    config_paths = PathsConfig(ratchetr_dir=repo_root / "config-home")

    working_dir = repo_root / "apps"
    working_dir.mkdir(exist_ok=True)

    resolved = resolve_paths(
        cli_overrides=overrides,
        env_overrides=env,
        config_paths=config_paths,
        cwd=working_dir,
    )

    assert resolved.tool_home == (working_dir / cli_tool_home).resolve()


@settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(env_manifest=_relative_paths())
def test_h_env_manifest_override_wins(env_manifest: Path, tmp_path: Path) -> None:
    repo_root = tmp_path
    env = EnvOverrides(
        config_path=None,
        repo_root=None,
        tool_home=None,
        manifest_path=env_manifest,
        cache_dir=None,
        log_dir=None,
        default_paths=None,
    )

    resolved = resolve_paths(
        env_overrides=env,
        config_paths=PathsConfig(),
        cwd=repo_root,
    )

    assert resolved.manifest_path == (repo_root / env_manifest).resolve()


@settings(max_examples=25, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(candidate_names=_ambiguous_candidate_names())
def test_h_discover_manifest_errors_on_multiple_candidates(candidate_names: list[str], tmp_path: Path) -> None:
    repo_root = tmp_path
    for name in candidate_names:
        candidate = repo_root / name
        candidate.parent.mkdir(parents=True, exist_ok=True)
        candidate.write_text("{}", encoding="utf-8")

    result = discover_manifest(_resolved_paths(repo_root))

    assert not result.found
    assert isinstance(result.error, ManifestDiscoveryError)
    assert result.diagnostics.ambiguity is not None
