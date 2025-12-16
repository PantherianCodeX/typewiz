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

"""Integration tests for runtime path resolution orchestration."""

from __future__ import annotations

from pathlib import Path

import pytest

from ratchetr.config import PathsConfig
from ratchetr.paths import EnvOverrides, PathOverrides, resolve_paths

pytestmark = pytest.mark.integration


def test_resolve_paths_prefers_cli_over_env_and_config(tmp_path: Path) -> None:
    repo_root = tmp_path
    cli_overrides = PathOverrides(
        repo_root=repo_root,
        tool_home=Path("cli_home"),
        manifest_path=Path("cli_manifest.json"),
        cache_dir=Path("cli_cache"),
        log_dir=Path("cli_logs"),
        config_path=Path("cli_config.toml"),
    )
    env_overrides = EnvOverrides(
        config_path=repo_root / "env.toml",
        repo_root=repo_root / "env_root",
        tool_home=repo_root / "env_home",
        manifest_path=repo_root / "env_manifest.json",
        cache_dir=repo_root / "env_cache",
        log_dir=repo_root / "env_logs",
        default_include=None,
    )
    config_paths = PathsConfig(
        ratchetr_dir=repo_root / "config_home",
        manifest_path=repo_root / "config_manifest.json",
        cache_dir=repo_root / "config_cache",
        log_dir=repo_root / "config_logs",
    )

    resolved = resolve_paths(
        cli_overrides=cli_overrides,
        env_overrides=env_overrides,
        config_paths=config_paths,
        cwd=repo_root,
    )

    assert resolved.repo_root == repo_root
    assert resolved.tool_home == (repo_root / "cli_home").resolve()
    assert resolved.cache_dir == (repo_root / "cli_cache").resolve()
    assert resolved.log_dir == (repo_root / "cli_logs").resolve()
    assert resolved.manifest_path == (repo_root / "cli_manifest.json").resolve()
    assert resolved.config_path == (repo_root / "cli_config.toml").resolve()


def test_resolve_paths_env_overrides_and_derives_defaults(tmp_path: Path) -> None:
    repo_root = tmp_path
    env_tool_home = repo_root / "env_home"
    env_overrides = EnvOverrides(
        config_path=None,
        repo_root=None,
        tool_home=env_tool_home,
        manifest_path=None,
        cache_dir=None,
        log_dir=None,
        default_include=None,
    )
    config_paths = PathsConfig(ratchetr_dir=repo_root / "config_home")

    resolved = resolve_paths(env_overrides=env_overrides, config_paths=config_paths, cwd=repo_root)

    assert resolved.repo_root == repo_root
    assert resolved.tool_home == env_tool_home.resolve()
    assert resolved.cache_dir == (env_tool_home / ".cache").resolve()
    assert resolved.log_dir == (env_tool_home / "logs").resolve()
    assert resolved.manifest_path == (env_tool_home / "manifest.json").resolve()


def test_resolve_paths_defaults_apply_when_empty(tmp_path: Path) -> None:
    repo_root = tmp_path
    resolved = resolve_paths(cli_overrides=PathOverrides(repo_root=repo_root), cwd=repo_root)

    assert resolved.tool_home == (repo_root / ".ratchetr").resolve()
    assert resolved.cache_dir == (repo_root / ".ratchetr" / ".cache").resolve()
    assert resolved.log_dir == (repo_root / ".ratchetr" / "logs").resolve()
    assert resolved.manifest_path == (repo_root / ".ratchetr" / "manifest.json").resolve()
    assert resolved.dashboard_path == (repo_root / ".ratchetr" / "dashboard.html").resolve()


def test_resolve_paths_prefers_env_root_and_config_directory(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text("", encoding="utf-8")
    env_root = tmp_path / "from_env"

    resolved_env = resolve_paths(
        env_overrides=EnvOverrides(
            config_path=None,
            repo_root=env_root,
            tool_home=None,
            manifest_path=None,
            cache_dir=None,
            log_dir=None,
            default_include=None,
        ),
        cwd=tmp_path,
    )
    assert resolved_env.repo_root == env_root.resolve()

    resolved_config = resolve_paths(
        env_overrides=EnvOverrides(
            config_path=None,
            repo_root=None,
            tool_home=None,
            manifest_path=None,
            cache_dir=None,
            log_dir=None,
            default_include=None,
        ),
        config_path=config_path,
        cwd=tmp_path,
    )
    assert resolved_config.repo_root == tmp_path.resolve()


def test_resolve_paths_config_override_relative_to_cwd(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    working_dir = repo_root / "pkg"
    working_dir.mkdir()
    cli_config = Path("../config.toml")
    overrides = PathOverrides(repo_root=repo_root, config_path=cli_config)

    resolved = resolve_paths(cli_overrides=overrides, cwd=working_dir)

    assert resolved.config_path == (working_dir / cli_config).resolve()


def test_resolve_paths_env_config_override_relative_to_cwd(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    working_dir = repo_root / "pkg"
    working_dir.mkdir()
    env_config = Path("../env-config.toml")
    env_overrides = EnvOverrides(
        config_path=env_config,
        repo_root=repo_root,
        tool_home=None,
        manifest_path=None,
        cache_dir=None,
        log_dir=None,
        default_include=None,
    )

    resolved = resolve_paths(env_overrides=env_overrides, cwd=working_dir)

    assert resolved.config_path == (working_dir / env_config).resolve()
