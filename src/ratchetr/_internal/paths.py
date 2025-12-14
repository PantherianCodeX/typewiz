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

"""Shared resolution utilities for ratchetr paths and artifacts."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

from ratchetr._internal.utils.paths import resolve_project_root
from ratchetr.compat import StrEnum
from ratchetr.config import PathsConfig
from ratchetr.config.constants import (
    DEFAULT_CACHE_DIRNAME,
    DEFAULT_DASHBOARD_FILENAME,
    DEFAULT_LOG_DIRNAME,
    DEFAULT_MANIFEST_FILENAME,
    DEFAULT_TOOL_HOME_DIRNAME,
)

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

logger: logging.Logger = logging.getLogger("ratchetr.paths")

CONFIG_ENV: Final[str] = "RATCHETR_CONFIG"
ROOT_ENV: Final[str] = "RATCHETR_ROOT"
TOOL_HOME_ENV: Final[str] = "RATCHETR_DIR"
MANIFEST_ENV: Final[str] = "RATCHETR_MANIFEST"
CACHE_ENV: Final[str] = "RATCHETR_CACHE_DIR"
LOG_ENV: Final[str] = "RATCHETR_LOG_DIR"
FULL_PATHS_ENV: Final[str] = "RATCHETR_FULL_PATHS"

MANIFEST_CANDIDATE_NAMES: Final[tuple[str, ...]] = (
    DEFAULT_MANIFEST_FILENAME,
    "typing_audit.json",
    "typing_audit_manifest.json",
    "reports/typing/typing_audit.json",
    "reports/typing/manifest.json",
)


@dataclass(slots=True, frozen=True)
class PathOverrides:
    """CLI-sourced overrides for core ratchetr paths."""

    config_path: Path | None = None
    repo_root: Path | None = None
    tool_home: Path | None = None
    manifest_path: Path | None = None
    cache_dir: Path | None = None
    log_dir: Path | None = None


@dataclass(slots=True, frozen=True)
class EnvOverrides:
    """Environment-sourced overrides for core ratchetr paths."""

    config_path: Path | None
    repo_root: Path | None
    tool_home: Path | None
    manifest_path: Path | None
    cache_dir: Path | None
    log_dir: Path | None
    full_paths: list[str] | None

    @classmethod
    def from_environ(cls, environ: Mapping[str, str] | None = None) -> EnvOverrides:
        """Create overrides from the current environment variables.

        Args:
            environ: Optional mapping to read environment variables from. Defaults
                to ``os.environ`` when not provided.

        Returns:
            EnvOverrides: Parsed environment overrides.
        """
        env = environ or os.environ
        tool_home = _path_from_env(env, TOOL_HOME_ENV)
        cache_dir = _path_from_env(env, CACHE_ENV)
        log_dir = _path_from_env(env, LOG_ENV)
        if tool_home is not None:
            cache_dir = cache_dir or (tool_home / DEFAULT_CACHE_DIRNAME)
            log_dir = log_dir or (tool_home / DEFAULT_LOG_DIRNAME)
        return cls(
            config_path=_path_from_env(env, CONFIG_ENV),
            repo_root=_path_from_env(env, ROOT_ENV),
            tool_home=tool_home,
            manifest_path=_path_from_env(env, MANIFEST_ENV),
            cache_dir=cache_dir,
            log_dir=log_dir,
            full_paths=_list_from_env(env, FULL_PATHS_ENV),
        )

    @property
    def active_overrides(self) -> dict[str, Path]:
        """Return a mapping of environment keys to resolved overrides.

        Returns:
            dict[str, Path]: Active environment overrides keyed by variable name.
        """
        mapping: dict[str, Path] = {}
        if self.config_path is not None:
            mapping[CONFIG_ENV] = self.config_path
        if self.repo_root is not None:
            mapping[ROOT_ENV] = self.repo_root
        if self.tool_home is not None:
            mapping[TOOL_HOME_ENV] = self.tool_home
        if self.manifest_path is not None:
            mapping[MANIFEST_ENV] = self.manifest_path
        if self.cache_dir is not None:
            mapping[CACHE_ENV] = self.cache_dir
        if self.log_dir is not None:
            mapping[LOG_ENV] = self.log_dir
        return mapping


@dataclass(slots=True, frozen=True)
class ResolvedPaths:
    """Resolved locations for repository-scoped artifacts."""

    repo_root: Path
    tool_home: Path
    cache_dir: Path
    log_dir: Path
    manifest_path: Path
    dashboard_path: Path
    config_path: Path | None


@dataclass(slots=True, frozen=True)
# ignore JUSTIFIED: diagnostics dataclass must capture all report fields together;
# splitting harms clarity
class ManifestDiagnostics:  # pylint: disable=too-many-instance-attributes
    """Diagnostics collected during manifest discovery."""

    repo_root: Path
    tool_home: Path
    config_path: Path | None
    cli_manifest: Path | None
    env_overrides: dict[str, Path]
    attempted_paths: tuple[Path, ...]
    matched_paths: tuple[Path, ...]
    glob_matches: tuple[Path, ...]
    ambiguity: str | None


@dataclass(slots=True, frozen=True)
class ManifestDiscoveryError:
    """Structured failure when manifest discovery cannot select a path."""

    message: str


@dataclass(slots=True, frozen=True)
class ManifestDiscoveryResult:
    """Result of manifest discovery including diagnostics."""

    manifest_path: Path | None
    diagnostics: ManifestDiagnostics
    error: ManifestDiscoveryError | None

    @property
    def found(self) -> bool:
        """Return True when a manifest path was successfully resolved.

        Returns:
            bool: True when discovery selected a manifest path.
        """
        return self.manifest_path is not None and self.error is None


class OutputFormat(StrEnum):
    """Supported output formats for save-style flags."""

    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"
    TEXT = "text"

    @classmethod
    def from_str(cls, raw: str) -> OutputFormat:
        """Create an OutputFormat from a user-provided string.

        Args:
            raw: Text representation of an output format.

        Returns:
            OutputFormat: Normalised output format value.

        Raises:
            ValueError: If the format cannot be parsed.
        """
        token = raw.strip().lower()
        try:
            return cls(token)
        # ignore JUSTIFIED: asserts defensive guard for invalid CLI inputs
        except ValueError as exc:  # pragma: no cover - runtime guard
            message = f"Unknown output format '{raw}'"
            raise ValueError(message) from exc


@dataclass(slots=True, frozen=True)
class OutputTarget:
    """Requested output target for a specific format."""

    format: OutputFormat
    path: Path | None = None


@dataclass(slots=True, frozen=True)
class OutputPlan:
    """Aggregated save requests for commands."""

    artifacts: tuple[OutputTarget, ...]
    dashboards: tuple[OutputTarget, ...] = ()


def resolve_paths(
    *,
    cli_overrides: PathOverrides | None = None,
    env_overrides: EnvOverrides | None = None,
    config_paths: PathsConfig | None = None,
    config_path: Path | None = None,
    cwd: Path | None = None,
) -> ResolvedPaths:
    """Resolve repository root and tool directories using unified precedence.

    Precedence for each resolved path is CLI overrides, then environment
    overrides, then configuration values, and finally defaults rooted at the
    discovered repository root.

    Args:
        cli_overrides: CLI-provided overrides, if any.
        env_overrides: Environment overrides; defaults to values derived from
            ``os.environ`` when omitted.
        config_paths: Filesystem configuration from ratchetr config.
        config_path: Path of the loaded configuration file, if available.
        cwd: Working directory used when discovering the repository root.

    Returns:
        ResolvedPaths: Effective locations for ratchetr artifacts.
    """
    cli = cli_overrides or PathOverrides()
    env = env_overrides or EnvOverrides.from_environ()
    config = (config_paths or PathsConfig()).with_defaults()
    working_dir = (cwd or Path.cwd()).resolve()

    env_cache = env.cache_dir or (env.tool_home / DEFAULT_CACHE_DIRNAME if env.tool_home else None)
    env_log = env.log_dir or (env.tool_home / DEFAULT_LOG_DIRNAME if env.tool_home else None)

    repo_root = _resolve_repo_root(cli.repo_root, env.repo_root, working_dir)
    tool_home = _resolve_overrides(
        cli_value=cli.tool_home,
        env_value=env.tool_home,
        config_value=config.ratchetr_dir,
        working_dir=working_dir,
        repo_root=repo_root,
    )
    if tool_home is None:
        tool_home = repo_root / DEFAULT_TOOL_HOME_DIRNAME
    cache_dir = _resolve_overrides(
        cli_value=cli.cache_dir,
        env_value=env_cache,
        config_value=config.cache_dir,
        working_dir=working_dir,
        repo_root=repo_root,
    )
    if cache_dir is None:
        cache_dir = tool_home / DEFAULT_CACHE_DIRNAME
    log_dir = _resolve_overrides(
        cli_value=cli.log_dir,
        env_value=env_log,
        config_value=config.log_dir,
        working_dir=working_dir,
        repo_root=repo_root,
    )
    if log_dir is None:
        log_dir = tool_home / DEFAULT_LOG_DIRNAME
    manifest_path = _resolve_overrides(
        cli_value=cli.manifest_path,
        env_value=env.manifest_path,
        config_value=config.manifest_path,
        working_dir=working_dir,
        repo_root=repo_root,
    )
    if manifest_path is None:
        manifest_path = tool_home / DEFAULT_MANIFEST_FILENAME
    dashboard_path = tool_home / DEFAULT_DASHBOARD_FILENAME
    cli_config_path = _resolve_optional(working_dir, cli.config_path)
    env_config_path = _resolve_optional(working_dir, env.config_path)
    return ResolvedPaths(
        repo_root=repo_root,
        tool_home=tool_home,
        cache_dir=cache_dir,
        log_dir=log_dir,
        manifest_path=manifest_path,
        dashboard_path=dashboard_path,
        config_path=cli_config_path or env_config_path or config_path,
    )


def discover_manifest(
    resolved: ResolvedPaths,
    *,
    cli_manifest: Path | None = None,
    env_overrides: EnvOverrides | None = None,
    config_manifest: Path | None = None,
    candidate_names: Sequence[str] = MANIFEST_CANDIDATE_NAMES,
) -> ManifestDiscoveryResult:
    """Discover an existing manifest path with diagnostics.

    Args:
        resolved: Pre-resolved core paths for the repository.
        cli_manifest: Explicit manifest path provided by the CLI, if any.
        env_overrides: Environment overrides, defaulting to ``os.environ``.
        config_manifest: Manifest path defined in configuration.
        candidate_names: Additional relative candidate names to probe.

    Returns:
        ManifestDiscoveryResult: Discovery outcome and diagnostic details.
    """
    env = env_overrides or EnvOverrides.from_environ()
    attempts: list[Path] = []
    matches: list[Path] = []
    seen: set[Path] = set()

    cli_result = _handle_cli_manifest(
        resolved=resolved,
        cli_manifest=cli_manifest,
        env=env,
        attempts=attempts,
        matches=matches,
        seen=seen,
    )
    if cli_result is not None:
        return cli_result

    for option in (env.manifest_path, config_manifest, resolved.manifest_path):
        if option is None:
            continue
        candidate = _record_candidate(_resolve_required(resolved.repo_root, option), attempts, matches, seen)
        if candidate.exists():
            diagnostics = _build_diagnostics(
                resolved,
                env,
                attempts,
                matches,
                cli_manifest=None,
                ambiguity=None,
            )
            return ManifestDiscoveryResult(manifest_path=candidate, diagnostics=diagnostics, error=None)

    for name in candidate_names:
        _record_candidate(resolved.repo_root / name, attempts, matches, seen)

    ambiguity = None
    error: ManifestDiscoveryError | None = None
    if len(matches) > 1:
        ambiguity = "Multiple manifests discovered; provide --manifest to choose one"
        error = ManifestDiscoveryError(message=ambiguity)
    diagnostics = _build_diagnostics(
        resolved,
        env,
        attempts,
        matches,
        cli_manifest=None,
        ambiguity=ambiguity,
    )
    if matches and error is None:
        return ManifestDiscoveryResult(manifest_path=matches[0], diagnostics=diagnostics, error=None)

    return ManifestDiscoveryResult(
        manifest_path=None,
        diagnostics=diagnostics,
        error=error or ManifestDiscoveryError(message="No manifest discovered"),
    )


def _record_candidate(path: Path, attempts: list[Path], matches: list[Path], seen: set[Path]) -> Path:
    absolute = path.resolve()
    if absolute in seen:
        return absolute
    seen.add(absolute)
    attempts.append(absolute)
    if absolute.exists():
        matches.append(absolute)
    return absolute


def _handle_cli_manifest(
    *,
    resolved: ResolvedPaths,
    cli_manifest: Path | None,
    env: EnvOverrides,
    attempts: list[Path],
    matches: list[Path],
    seen: set[Path],
) -> ManifestDiscoveryResult | None:
    if cli_manifest is None:
        return None

    candidate = _record_candidate(_resolve_required(resolved.repo_root, cli_manifest), attempts, matches, seen)
    diagnostics = _build_diagnostics(resolved, env, attempts, matches, cli_manifest=candidate, ambiguity=None)
    if candidate.exists():
        return ManifestDiscoveryResult(manifest_path=candidate, diagnostics=diagnostics, error=None)
    return ManifestDiscoveryResult(
        manifest_path=None,
        diagnostics=diagnostics,
        error=ManifestDiscoveryError(message=f"Manifest not found at {candidate}"),
    )


def _build_diagnostics(
    resolved: ResolvedPaths,
    env: EnvOverrides,
    attempts: Sequence[Path],
    matches: Sequence[Path],
    *,
    cli_manifest: Path | None,
    ambiguity: str | None,
) -> ManifestDiagnostics:
    glob_matches = _discover_globs(resolved)
    return ManifestDiagnostics(
        repo_root=resolved.repo_root,
        tool_home=resolved.tool_home,
        config_path=resolved.config_path,
        cli_manifest=cli_manifest,
        env_overrides=env.active_overrides,
        attempted_paths=tuple(attempts),
        matched_paths=tuple(matches),
        glob_matches=glob_matches,
        ambiguity=ambiguity,
    )


def _discover_globs(resolved: ResolvedPaths) -> tuple[Path, ...]:
    globbed: list[Path] = []
    globbed.extend(sorted(resolved.tool_home.glob("manifest*.json")))
    globbed.extend(sorted(resolved.repo_root.glob("typing_audit*.json")))
    return tuple(Path(path).resolve() for path in globbed)


def _resolve_repo_root(
    cli_root: Path | None,
    env_root: Path | None,
    cwd: Path,
) -> Path:
    if cli_root is not None:
        resolved = _resolve_required(cwd, cli_root)
        logger.debug("Using root from CLI override: %s", resolved)
        return resolved
    if env_root is not None:
        resolved = _resolve_required(cwd, env_root)
        logger.debug("Using root from environment variable: %s", resolved)
        return resolved
    discovered = resolve_project_root(cwd)
    logger.debug("Using root from discovery: %s", discovered)
    return discovered


def _resolve_overrides(
    *,
    cli_value: Path | None,
    env_value: Path | None,
    config_value: Path | None,
    working_dir: Path,
    repo_root: Path,
) -> Path | None:
    if cli_value is not None:
        return _resolve_optional(working_dir, cli_value)
    if env_value is not None:
        return _resolve_optional(working_dir, env_value)
    if config_value is not None:
        return _resolve_optional(repo_root, config_value)
    return None


def _resolve_optional(base_dir: Path, candidate: Path | None) -> Path | None:
    if candidate is None:
        return None
    return candidate if candidate.is_absolute() else (base_dir / candidate).resolve()


def _resolve_required(base_dir: Path, candidate: Path) -> Path:
    return candidate if candidate.is_absolute() else (base_dir / candidate).resolve()


def _path_from_env(environ: Mapping[str, str], name: str) -> Path | None:
    raw = environ.get(name)
    if raw is None:
        return None
    value = raw.strip()
    if not value:
        return None
    return Path(value)


def _list_from_env(environ: Mapping[str, str], name: str) -> list[str] | None:
    """Parse a list of strings from an environment variable.

    Args:
        environ: Environment mapping to read from.
        name: Name of the environment variable.

    Returns:
        List of non-empty strings split by commas or colons, or None if the
        variable is not set or empty.
    """
    raw = environ.get(name)
    if raw is None:
        return None
    value = raw.strip()
    if not value:
        return None
    separator = ":" if ":" in value and "," not in value else ","
    parts = [part.strip() for part in value.split(separator)]
    result = [part for part in parts if part]
    return result or None


__all__ = [
    "CACHE_ENV",
    "CONFIG_ENV",
    "DEFAULT_CACHE_DIRNAME",
    "DEFAULT_DASHBOARD_FILENAME",
    "DEFAULT_LOG_DIRNAME",
    "DEFAULT_MANIFEST_FILENAME",
    "DEFAULT_TOOL_HOME_DIRNAME",
    "LOG_ENV",
    "MANIFEST_CANDIDATE_NAMES",
    "MANIFEST_ENV",
    "ROOT_ENV",
    "TOOL_HOME_ENV",
    "EnvOverrides",
    "ManifestDiagnostics",
    "ManifestDiscoveryError",
    "ManifestDiscoveryResult",
    "OutputFormat",
    "OutputPlan",
    "OutputTarget",
    "PathOverrides",
    "ResolvedPaths",
    "discover_manifest",
    "resolve_paths",
]
