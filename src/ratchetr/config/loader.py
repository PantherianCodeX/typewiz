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

"""Configuration loading and path resolution for ratchetr.

This module provides functionality to load ratchetr configuration files from disk,
validate them, and resolve relative paths to absolute paths. It supports both
project-level configuration files (ratchetr.toml, .ratchetr.toml) and directory-level
overrides (ratchetr.dir.toml, .ratchetrdir.toml).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final, Literal, TypeAlias, cast

from pydantic import ValidationError

from ratchetr.compat import tomllib
from ratchetr.core.type_aliases import EngineName, RunnerName
from ratchetr.runtime import resolve_project_root

from .models import (
    AuditConfig,
    Config,
    ConfigModel,
    ConfigReadError,
    DirectoryOverrideValidationError,
    EngineSettings,
    InvalidConfigFileError,
    PathOverride,
    PathOverrideModel,
    PathsConfig,
    RatchetConfig,
    model_to_dataclass,
    path_override_from_model,
    paths_from_model,
    ratchet_from_model,
)

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(slots=True, frozen=True)
class LoadedConfig:
    """Container for a loaded configuration and its source path.

    Attributes:
        config: Parsed configuration instance.
        path: Filesystem path the configuration was loaded from, or None when
            defaults are used.
    """

    config: Config
    path: Path | None


def resolve_path_fields(base_dir: Path, audit: AuditConfig) -> None:
    """Resolve all relative paths in audit configuration to absolute paths.

    This function recursively resolves relative paths in the audit configuration,
    including output paths, engine settings paths, and path override fields. All
    relative paths are resolved relative to the provided base directory.

    Args:
        base_dir: The base directory to resolve relative paths against.
        audit: The audit configuration containing paths to resolve.
    """
    _resolve_output_paths(base_dir, audit)
    for settings in audit.engine_settings.values():
        _resolve_engine_settings_paths(base_dir, settings)
    _resolve_path_override_fields(base_dir, audit.path_overrides)


def _resolve_output_paths(base_dir: Path, audit: AuditConfig) -> None:
    for field_name in ("manifest_path", "dashboard_json", "dashboard_markdown", "dashboard_html"):
        value = getattr(audit, field_name)
        setattr(audit, field_name, _resolved_path(base_dir, value))


def _resolve_engine_settings_paths(base_dir: Path, settings: EngineSettings) -> None:
    settings.config_file = _resolved_path(base_dir, settings.config_file)
    for profile in settings.profiles.values():
        profile.config_file = _resolved_path(base_dir, profile.config_file)


def _resolve_path_override_fields(base_dir: Path, overrides: Sequence[PathOverride]) -> None:
    for override in overrides:
        override.path = _resolved_required_path(base_dir, override.path)
        for settings in override.engine_settings.values():
            _resolve_engine_settings_paths(override.path, settings)


def _resolved_path(base_dir: Path, value: Path | None) -> Path | None:
    if value is None:
        return None
    return value if value.is_absolute() else (base_dir / value).resolve()


def _resolved_required_path(base_dir: Path, value: Path) -> Path:
    return value if value.is_absolute() else (base_dir / value).resolve()


def _resolve_ratchet_paths(base_dir: Path, ratchet: RatchetConfig) -> None:
    if ratchet.manifest_path and not ratchet.manifest_path.is_absolute():
        ratchet.manifest_path = (base_dir / ratchet.manifest_path).resolve()
    if ratchet.output_path and not ratchet.output_path.is_absolute():
        ratchet.output_path = (base_dir / ratchet.output_path).resolve()


def _discover_path_overrides(root: Path) -> list[PathOverride]:
    overrides: list[PathOverride] = []
    for filename in FOLDER_CONFIG_FILENAMES:
        try:
            candidates = sorted(root.rglob(filename))
        except FileNotFoundError:
            # ignore JUSTIFIED: intermediate folders may be removed by tools (e.g. hypothesis)
            # during traversal; skip missing paths and continue scanning
            continue
        for config_path in candidates:
            if not config_path.is_file():
                continue
            directory = config_path.parent.resolve()
            try:
                raw = tomllib.loads(config_path.read_text(encoding="utf-8"))
            # ignore JUSTIFIED: config files may be unreadable or malformed
            # convert parsing issues to ConfigReadError
            except Exception as exc:  # pragma: no cover - IO errors
                raise ConfigReadError(config_path, exc) from exc
            try:
                model = PathOverrideModel.model_validate(raw)
            except ValidationError as exc:
                raise DirectoryOverrideValidationError(config_path, exc) from exc
            override = path_override_from_model(directory, model)
            overrides.append(override)
    overrides.sort(key=lambda item: (len(item.path.parts), item.path.as_posix()))
    return overrides


def load_config(explicit_path: Path | None = None) -> Config:
    """Load ratchetr configuration from a TOML file or use defaults.

    Args:
        explicit_path: Optional explicit path to a configuration file. If provided,
            only this file will be checked. If None, standard locations are searched.

    Returns:
        A Config object containing audit and ratchet configuration with all paths
        resolved to absolute paths.
    """
    return load_config_with_metadata(explicit_path).config


def load_config_with_metadata(explicit_path: Path | None = None) -> LoadedConfig:
    """Load ratchetr configuration with metadata about the source file.

    This function searches for and loads a ratchetr configuration file, resolves
    all relative paths, discovers directory-level path overrides, and returns a
    fully configured Config object alongside the path it was loaded from. If no
    configuration file is found, it returns a default configuration with sensible
    defaults and a ``None`` path.

    The function searches for configuration files in the following order:
    1. If explicit_path is provided, only that path is checked.
    2. Otherwise, ratchetr.toml, .ratchetr.toml, and pyproject.toml are searched
       within the detected project root (based on repository markers), using the
       first file that contains ratchetr configuration data.

    Configuration files can use either a direct format (recommended for standalone
    ``ratchetr.toml`` files) or be nested under ``[tool.ratchetr]`` for
    compatibility with PEP 518 tools. When both a
    standalone file and pyproject.toml contain ratchetr configuration, the
    standalone file takes precedence because it is earlier in the search order.

    Args:
        explicit_path: Optional explicit path to a configuration file. If provided,
            only this file will be checked. If None, standard locations are searched.

    Returns:
        LoadedConfig: Parsed configuration and the path it originated from.
    """
    base_dir = _discover_config_root(explicit_path)
    search_order = _config_search_order(base_dir, explicit_path)

    for candidate in search_order:
        candidate_config = _load_candidate_config(candidate, explicit=explicit_path is not None)
        if candidate_config is not None:
            return candidate_config

    return _default_config(base_dir)


def _default_config(base_dir: Path) -> LoadedConfig:
    cfg = Config()
    cfg.audit.runners = [
        RunnerName(EngineName("pyright")),
        RunnerName(EngineName("mypy")),
    ]
    cfg.audit.path_overrides = _discover_path_overrides(base_dir)
    resolve_path_fields(base_dir, cfg.audit)
    _resolve_ratchet_paths(base_dir, cfg.ratchet)
    cfg.paths = PathsConfig()
    return LoadedConfig(config=cfg, path=None)


def _discover_config_root(explicit_path: Path | None) -> Path:
    if explicit_path:
        return _resolve_candidate_path(explicit_path).parent.resolve()
    return resolve_project_root(Path.cwd())


def _config_search_order(base_dir: Path, explicit_path: Path | None) -> list[Path]:
    if explicit_path:
        return [_resolve_candidate_path(explicit_path)]
    return [
        base_dir / "ratchetr.toml",
        base_dir / ".ratchetr.toml",
        base_dir / "pyproject.toml",
    ]


def _resolve_candidate_path(candidate: Path) -> Path:
    return candidate if candidate.is_absolute() else (Path.cwd() / candidate).resolve()


def _load_candidate_config(candidate: Path, *, explicit: bool) -> LoadedConfig | None:
    if not candidate.exists():
        return None
    try:
        raw_map: dict[str, object] = tomllib.loads(candidate.read_text(encoding="utf-8"))
    # ignore JUSTIFIED: filesystem or parse errors depend on host configuration
    except Exception as exc:  # pragma: no cover - IO errors
        raise ConfigReadError(candidate, exc) from exc

    payload = _extract_ratchetr_payload(candidate, raw_map)
    if payload is None:
        if explicit:
            message = (
                f"{candidate.name} does not define ratchetr configuration; "
                "add standard tables (e.g. [audit]) or a [tool.ratchetr] section"
            )
            raise InvalidConfigFileError(candidate, ValueError(message))
        return None

    try:
        cfg_model = ConfigModel.model_validate(payload)
    # ignore JUSTIFIED: configuration files may be invalid; raise structured error
    except ValidationError as exc:  # pragma: no cover - configuration errors
        raise InvalidConfigFileError(candidate, exc) from exc

    audit = model_to_dataclass(cfg_model.audit)
    ratchet = ratchet_from_model(cfg_model.ratchet)
    root = candidate.parent.resolve()
    paths = paths_from_model(root, cfg_model.paths)
    audit.path_overrides = _discover_path_overrides(root)
    resolve_path_fields(root, audit)
    _resolve_ratchet_paths(root, ratchet)
    config = Config(audit=audit, ratchet=ratchet, paths=paths)
    return LoadedConfig(config=config, path=candidate.resolve())


def _extract_ratchetr_payload(candidate: Path, raw_map: dict[str, object]) -> dict[str, object] | None:
    """Extract the ratchetr configuration payload from a TOML mapping.

    Args:
        candidate: Source configuration path.
        raw_map: Data parsed from the TOML document.

    Returns:
        Mapping to validate or None when no ratchetr configuration is present (only for
        pyproject.toml lookups).

    Raises:
        InvalidConfigFileError: If [tool.ratchetr] exists but is not a table.
    """
    tool_section_raw = raw_map.get("tool")
    is_pyproject = candidate.name == "pyproject.toml"
    if tool_section_raw is not None and not isinstance(tool_section_raw, dict):
        if is_pyproject:
            message = "[tool] in pyproject.toml must be a TOML table"
            raise InvalidConfigFileError(candidate, ValueError(message))
        # standalone configs ignore unrelated tool entries
        tool_section_raw = None

    ratchetr_section: object | None = None
    tool_section: dict[str, object] | None = None
    if isinstance(tool_section_raw, dict):
        tool_section = cast("dict[str, object]", tool_section_raw)
        ratchetr_section = tool_section.get("ratchetr")
        if ratchetr_section is not None and not isinstance(ratchetr_section, dict):
            message = "[tool.ratchetr] must be a TOML table"
            raise InvalidConfigFileError(candidate, ValueError(message))
        if isinstance(ratchetr_section, dict):
            return cast("dict[str, object]", ratchetr_section)

    if is_pyproject:
        return None
    return raw_map


FolderConfigFilename: TypeAlias = Literal["ratchetr.dir.toml", ".ratchetrdir.toml"]
FOLDER_CONFIG_FILENAMES: Final[tuple[FolderConfigFilename, FolderConfigFilename]] = (
    "ratchetr.dir.toml",
    ".ratchetrdir.toml",
)

__all__ = ["LoadedConfig", "load_config", "load_config_with_metadata", "resolve_path_fields"]
