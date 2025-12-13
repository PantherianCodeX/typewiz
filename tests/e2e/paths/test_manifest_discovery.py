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

"""End-to-end coverage for manifest discovery workflows."""

from __future__ import annotations

from pathlib import Path

import pytest

from ratchetr.paths import EnvOverrides, ManifestDiscoveryError, ResolvedPaths, discover_manifest

pytestmark = [pytest.mark.e2e, pytest.mark.integration]


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
