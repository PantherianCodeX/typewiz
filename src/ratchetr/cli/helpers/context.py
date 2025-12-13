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

"""CLI context and manifest discovery helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from ratchetr.cli.helpers.io import echo
from ratchetr.config.loader import load_config_with_metadata
from ratchetr.paths import (
    EnvOverrides,
    ManifestDiscoveryResult,
    PathOverrides,
    ResolvedPaths,
    discover_manifest,
    resolve_paths,
)

if TYPE_CHECKING:
    from ratchetr.config import Config


@dataclass(slots=True, frozen=True)
class CLIContext:
    """Resolved configuration and paths shared by CLI commands."""

    config: Config
    config_path: Path | None
    resolved_paths: ResolvedPaths
    env_overrides: EnvOverrides


def build_cli_context(
    overrides: PathOverrides,
    *,
    cwd: Path | None = None,
) -> CLIContext:
    """Build a CLI context using unified precedence across CLI/env/config.

    Args:
        overrides: CLI-provided path overrides.
        cwd: Optional working directory to use for resolution.

    Returns:
        CLIContext: Resolved configuration, paths, and environment overrides.
    """
    env_overrides = EnvOverrides.from_environ()
    working_dir = (cwd or Path.cwd()).resolve()
    search_root = _determine_config_search_root(overrides, env_overrides, working_dir)
    config_hint = overrides.config_path or env_overrides.config_path
    loaded = load_config_with_metadata(config_hint, search_root=search_root, cwd=working_dir)
    resolved_paths = resolve_paths(
        cli_overrides=overrides,
        env_overrides=env_overrides,
        config_paths=loaded.config.paths,
        config_path=loaded.path,
        cwd=working_dir,
    )
    return CLIContext(
        config=loaded.config,
        config_path=loaded.path,
        resolved_paths=resolved_paths,
        env_overrides=env_overrides,
    )


def discover_manifest_or_exit(
    context: CLIContext,
    *,
    cli_manifest: Path | None,
) -> Path:
    """Discover a manifest path or exit with diagnostics.

    Args:
        context: Shared CLI context containing resolved paths and environment overrides.
        cli_manifest: Optional manifest path provided on the CLI.

    Returns:
        Path: Resolved manifest path when discovery succeeds.

    Raises:
        SystemExit: If manifest discovery fails after emitting diagnostics.
    """
    result = discover_manifest(
        context.resolved_paths,
        cli_manifest=cli_manifest,
        env_overrides=context.env_overrides,
        config_manifest=context.config.paths.manifest_path,
    )
    if result.found and result.manifest_path is not None:
        return result.manifest_path
    emit_manifest_diagnostics(result)
    raise SystemExit(2)


def emit_manifest_diagnostics(result: ManifestDiscoveryResult) -> None:
    """Print manifest discovery diagnostics for user feedback.

    Args:
        result: Discovery outcome containing diagnostics and any errors.
    """
    diagnostics = result.diagnostics
    echo("[ratchetr] manifest discovery failed")
    if result.error is not None:
        echo(f"  reason: {result.error.message}")
    echo(f"  repo root: {diagnostics.repo_root}")
    echo(f"  tool home: {diagnostics.tool_home}")
    echo(f"  config: {diagnostics.config_path or '<none>'}")
    if diagnostics.cli_manifest is not None:
        echo(f"  cli manifest: {diagnostics.cli_manifest}")
    if diagnostics.env_overrides:
        env_lines = ", ".join(f"{key}={value}" for key, value in diagnostics.env_overrides.items())
        echo(f"  env overrides: {env_lines}")
    if diagnostics.attempted_paths:
        echo("  attempted paths:")
        for path in diagnostics.attempted_paths:
            echo(f"    - {path}")
    if diagnostics.glob_matches:
        echo("  glob matches:")
        for path in diagnostics.glob_matches:
            echo(f"    - {path}")
    if diagnostics.ambiguity:
        echo(f"  ambiguity: {diagnostics.ambiguity}")


def _determine_config_search_root(
    cli_overrides: PathOverrides,
    env_overrides: EnvOverrides,
    working_dir: Path,
) -> Path | None:
    """Resolve the search root for configuration discovery.

    Returns:
        Optional absolute Path to use as the config search base.
    """
    for candidate in (cli_overrides.repo_root, env_overrides.repo_root):
        if candidate is None:
            continue
        return candidate if candidate.is_absolute() else (working_dir / candidate).resolve()
    return None


__all__ = ["CLIContext", "build_cli_context", "discover_manifest_or_exit", "emit_manifest_diagnostics"]
