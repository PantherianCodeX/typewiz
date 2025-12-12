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

from __future__ import annotations

from pathlib import Path

import pytest

from ratchetr.config import PathsConfig
from ratchetr.paths import (
    EnvOverrides,
    ManifestDiscoveryError,
    OutputFormat,
    PathOverrides,
    ResolvedPaths,
    discover_manifest,
    resolve_paths,
)

pytestmark = pytest.mark.unit


def _resolved_paths(repo_root: Path, tool_home: Path | None = None) -> ResolvedPaths:
    home = tool_home or repo_root / ".ratchetr"
    return ResolvedPaths(
        repo_root=repo_root,
        tool_home=home,
        cache_dir=home / ".cache",
        log_dir=home / "logs",
        manifest_path=home / "manifest.json",
        dashboard_path=home / "dashboard.html",
        config_path=None,
    )


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


def test_discover_manifest_prefers_env_manifest_without_ambiguity(tmp_path: Path) -> None:
    repo_root = tmp_path
    tool_home = repo_root / ".ratchetr"
    tool_home.mkdir()
    env_manifest = repo_root / "env_manifest.json"
    env_manifest.write_text("{}", encoding="utf-8")
    default_manifest = tool_home / "manifest.json"
    default_manifest.write_text("{}", encoding="utf-8")

    resolved = _resolved_paths(repo_root, tool_home)
    env_overrides = EnvOverrides(
        config_path=None,
        repo_root=None,
        tool_home=None,
        manifest_path=env_manifest,
        cache_dir=None,
        log_dir=None,
    )

    result = discover_manifest(
        resolved,
        env_overrides=env_overrides,
        config_manifest=repo_root / "reports" / "typing" / "manifest.json",
    )

    assert result.found
    assert result.manifest_path == env_manifest.resolve()
    assert result.error is None
    assert env_manifest.resolve() in result.diagnostics.attempted_paths
    assert default_manifest.resolve() in result.diagnostics.glob_matches
    assert result.diagnostics.ambiguity is None


def test_discover_manifest_errors_on_ambiguous_candidates(tmp_path: Path) -> None:
    repo_root = tmp_path
    manifest_a = repo_root / "typing_audit.json"
    manifest_b = repo_root / "reports" / "typing" / "typing_audit.json"
    manifest_b.parent.mkdir(parents=True, exist_ok=True)
    manifest_a.write_text("{}", encoding="utf-8")
    manifest_b.write_text("{}", encoding="utf-8")
    resolved = _resolved_paths(repo_root)

    result = discover_manifest(resolved)

    assert not result.found
    assert isinstance(result.error, ManifestDiscoveryError)
    assert "Multiple manifests" in result.error.message
    assert result.diagnostics.ambiguity is not None
    assert len(result.diagnostics.matched_paths) >= 2


def test_discover_manifest_handles_missing_cli_override(tmp_path: Path) -> None:
    repo_root = tmp_path
    resolved = _resolved_paths(repo_root)

    result = discover_manifest(resolved, cli_manifest=Path("missing.json"))

    assert not result.found
    assert isinstance(result.error, ManifestDiscoveryError)
    assert (repo_root / "missing.json").resolve() in result.diagnostics.attempted_paths
    assert result.diagnostics.cli_manifest == (repo_root / "missing.json").resolve()


def test_discover_manifest_records_cli_manifest_on_success(tmp_path: Path) -> None:
    repo_root = tmp_path
    manifest_path = repo_root / "manifest.json"
    manifest_path.write_text("{}", encoding="utf-8")
    resolved = _resolved_paths(repo_root)

    result = discover_manifest(resolved, cli_manifest=Path("manifest.json"))

    assert result.found
    assert result.diagnostics.cli_manifest == manifest_path.resolve()


def test_output_format_from_str_validates() -> None:
    assert OutputFormat.from_str("JSON") is OutputFormat.JSON
    with pytest.raises(ValueError, match="Unknown output format"):
        OutputFormat.from_str("yaml")


def test_env_overrides_from_environ_derives_cache_and_active_overrides(tmp_path: Path) -> None:
    env_home = tmp_path / "env_home"
    environ = {
        "RATCHETR_DIR": str(env_home),
        "RATCHETR_CONFIG": str(tmp_path / "config.toml"),
        "RATCHETR_ROOT": str(tmp_path),
        "RATCHETR_MANIFEST": str(tmp_path / "manifest.json"),
        "RATCHETR_CACHE_DIR": "",  # intentionally blank
    }

    overrides = EnvOverrides.from_environ(environ)

    assert overrides.cache_dir == env_home / ".cache"
    assert overrides.log_dir == env_home / "logs"
    assert overrides.active_overrides == {
        "RATCHETR_CONFIG": (tmp_path / "config.toml").resolve(),
        "RATCHETR_ROOT": tmp_path.resolve(),
        "RATCHETR_DIR": env_home.resolve(),
        "RATCHETR_MANIFEST": (tmp_path / "manifest.json").resolve(),
        "RATCHETR_LOG_DIR": (env_home / "logs").resolve(),
        "RATCHETR_CACHE_DIR": (env_home / ".cache").resolve(),
    }


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
    )

    resolved = resolve_paths(env_overrides=env_overrides, cwd=working_dir)

    assert resolved.config_path == (working_dir / env_config).resolve()


def test_discover_manifest_prefers_cli_manifest_when_present(tmp_path: Path) -> None:
    repo_root = tmp_path
    manifest = repo_root / "explicit.json"
    manifest.write_text("{}", encoding="utf-8")
    resolved = _resolved_paths(repo_root)

    result = discover_manifest(resolved, cli_manifest=manifest)

    assert result.manifest_path == manifest.resolve()
    assert result.diagnostics.ambiguity is None


def test_discover_manifest_considers_configured_manifest(tmp_path: Path) -> None:
    repo_root = tmp_path
    manifest = repo_root / "configured.json"
    manifest.write_text("{}", encoding="utf-8")
    resolved = _resolved_paths(repo_root)

    result = discover_manifest(resolved, config_manifest=manifest)

    assert result.manifest_path == manifest.resolve()
    assert manifest.resolve() in result.diagnostics.attempted_paths
