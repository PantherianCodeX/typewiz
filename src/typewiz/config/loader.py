from __future__ import annotations

import tomllib as toml
from pathlib import Path
from typing import Final, Literal, cast

from pydantic import ValidationError

from typewiz.core.type_aliases import EngineName, RunnerName

from .models import (
    AuditConfig,
    Config,
    ConfigModel,
    ConfigReadError,
    DirectoryOverrideValidationError,
    InvalidConfigFileError,
    PathOverride,
    PathOverrideModel,
    RatchetConfig,
    model_to_dataclass,
    path_override_from_model,
    ratchet_from_model,
)


def resolve_path_fields(base_dir: Path, audit: AuditConfig) -> None:
    for field_name in ("manifest_path", "dashboard_json", "dashboard_markdown", "dashboard_html"):
        value = getattr(audit, field_name)
        if value is None:
            continue
        if not value.is_absolute():
            resolved = (base_dir / value).resolve()
            setattr(audit, field_name, resolved)
    for settings in audit.engine_settings.values():
        if settings.config_file and not settings.config_file.is_absolute():
            settings.config_file = (base_dir / settings.config_file).resolve()
        for profile in settings.profiles.values():
            if profile.config_file and not profile.config_file.is_absolute():
                profile.config_file = (base_dir / profile.config_file).resolve()
    for override in audit.path_overrides:
        if not override.path.is_absolute():
            override.path = (base_dir / override.path).resolve()
        for settings in override.engine_settings.values():
            if settings.config_file and not settings.config_file.is_absolute():
                settings.config_file = (override.path / settings.config_file).resolve()
            for profile in settings.profiles.values():
                if profile.config_file and not profile.config_file.is_absolute():
                    profile.config_file = (override.path / profile.config_file).resolve()


def _resolve_ratchet_paths(base_dir: Path, ratchet: RatchetConfig) -> None:
    if ratchet.manifest_path and not ratchet.manifest_path.is_absolute():
        ratchet.manifest_path = (base_dir / ratchet.manifest_path).resolve()
    if ratchet.output_path and not ratchet.output_path.is_absolute():
        ratchet.output_path = (base_dir / ratchet.output_path).resolve()


def _discover_path_overrides(root: Path) -> list[PathOverride]:
    overrides: list[PathOverride] = []
    for filename in FOLDER_CONFIG_FILENAMES:
        for config_path in sorted(root.rglob(filename)):
            if not config_path.is_file():
                continue
            directory = config_path.parent.resolve()
            try:
                raw = toml.loads(config_path.read_text(encoding="utf-8"))
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
    search_order: list[Path] = []
    if explicit_path:
        search_order.append(explicit_path)
    else:
        search_order.extend((Path("typewiz.toml"), Path(".typewiz.toml")))

    for candidate in search_order:
        if not candidate.exists():
            continue
        raw_map: dict[str, object] = toml.loads(candidate.read_text(encoding="utf-8"))
        tool_obj = raw_map.get("tool")
        if isinstance(tool_obj, dict):
            tool_section_any = cast("dict[str, object]", tool_obj).get("typewiz")
            if isinstance(tool_section_any, dict):
                raw_map = cast("dict[str, object]", tool_section_any)
        try:
            cfg_model = ConfigModel.model_validate(raw_map)
        except ValidationError as exc:  # pragma: no cover - configuration errors
            raise InvalidConfigFileError(candidate, exc) from exc
        audit = model_to_dataclass(cfg_model.audit)
        ratchet = ratchet_from_model(cfg_model.ratchet)
        root = candidate.parent.resolve()
        audit.path_overrides = _discover_path_overrides(root)
        resolve_path_fields(root, audit)
        _resolve_ratchet_paths(root, ratchet)
        return Config(audit=audit, ratchet=ratchet)

    root = Path.cwd().resolve()
    cfg = Config()
    cfg.audit.runners = [
        RunnerName(EngineName("pyright")),
        RunnerName(EngineName("mypy")),
    ]
    cfg.audit.path_overrides = _discover_path_overrides(root)
    resolve_path_fields(root, cfg.audit)
    _resolve_ratchet_paths(root, cfg.ratchet)
    return cfg


type FolderConfigFilename = Literal["typewiz.dir.toml", ".typewizdir.toml"]
FOLDER_CONFIG_FILENAMES: Final[tuple[FolderConfigFilename, FolderConfigFilename]] = (
    "typewiz.dir.toml",
    ".typewizdir.toml",
)

__all__ = ["load_config", "resolve_path_fields"]
