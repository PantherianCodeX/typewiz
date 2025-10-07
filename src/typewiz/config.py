from __future__ import annotations

import tomllib as toml
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

CONFIG_VERSION = 0


def _default_list_str() -> list[str]:
    return []


@dataclass(slots=True)
class EngineProfile:
    inherit: str | None = None
    plugin_args: list[str] = field(default_factory=_default_list_str)
    config_file: Path | None = None
    include: list[str] = field(default_factory=_default_list_str)
    exclude: list[str] = field(default_factory=_default_list_str)


def _default_dict_str_engineprofile() -> dict[str, EngineProfile]:
    return {}


@dataclass(slots=True)
class EngineSettings:
    plugin_args: list[str] = field(default_factory=_default_list_str)
    config_file: Path | None = None
    include: list[str] = field(default_factory=_default_list_str)
    exclude: list[str] = field(default_factory=_default_list_str)
    default_profile: str | None = None
    profiles: dict[str, EngineProfile] = field(default_factory=_default_dict_str_engineprofile)


def _default_dict_str_liststr() -> dict[str, list[str]]:
    return {}


def _default_dict_str_enginesettings() -> dict[str, EngineSettings]:
    return {}


def _default_dict_str_str() -> dict[str, str]:
    return {}


def _default_list_path_override() -> list[PathOverride]:
    return []


@dataclass(slots=True)
class AuditConfig:
    manifest_path: Path | None = None
    full_paths: list[str] | None = None
    max_depth: int | None = None
    max_files: int | None = None
    max_bytes: int | None = None
    skip_current: bool | None = None
    skip_full: bool | None = None
    fail_on: str | None = None
    dashboard_json: Path | None = None
    dashboard_markdown: Path | None = None
    dashboard_html: Path | None = None
    respect_gitignore: bool | None = None
    runners: list[str] | None = None
    plugin_args: dict[str, list[str]] = field(default_factory=_default_dict_str_liststr)
    engine_settings: dict[str, EngineSettings] = field(
        default_factory=_default_dict_str_enginesettings
    )
    active_profiles: dict[str, str] = field(default_factory=_default_dict_str_str)
    path_overrides: list[PathOverride] = field(default_factory=_default_list_path_override)


@dataclass(slots=True)
class Config:
    audit: AuditConfig = field(default_factory=AuditConfig)


@dataclass(slots=True)
class PathOverride:
    path: Path
    engine_settings: dict[str, EngineSettings] = field(
        default_factory=_default_dict_str_enginesettings
    )
    active_profiles: dict[str, str] = field(default_factory=_default_dict_str_str)


def _ensure_list(value: object | None) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if not isinstance(value, Iterable):
        return []
    result: list[str] = []
    for item in cast(Iterable[object], value):
        if isinstance(item, str):
            stripped = item.strip()
            if stripped:
                result.append(stripped)
    return result


def _dedupe_preserve(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


class EngineProfileModel(BaseModel):
    inherit: str | None = None
    plugin_args: list[str] = Field(default_factory=list)
    config_file: Path | None = None
    include: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)

    @field_validator("plugin_args", "include", "exclude", mode="before")
    @classmethod
    def _coerce_list(cls, value: object) -> list[str]:
        return _ensure_list(value) or []

    @field_validator("inherit", mode="before")
    @classmethod
    def _strip_inherit(cls, value: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        raise ValueError("inherit must be a string")

    @model_validator(mode="after")
    def _normalise(self) -> EngineProfileModel:
        object.__setattr__(self, "plugin_args", _dedupe_preserve(self.plugin_args))
        object.__setattr__(self, "include", _dedupe_preserve(self.include))
        object.__setattr__(self, "exclude", _dedupe_preserve(self.exclude))
        return self


class EngineSettingsModel(BaseModel):
    plugin_args: list[str] = Field(default_factory=list)
    config_file: Path | None = None
    include: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)
    default_profile: str | None = None
    profiles: dict[str, EngineProfileModel] = Field(default_factory=dict)

    @field_validator("plugin_args", "include", "exclude", mode="before")
    @classmethod
    def _coerce_list(cls, value: object) -> list[str]:
        return _ensure_list(value) or []

    @field_validator("default_profile", mode="before")
    @classmethod
    def _strip_default_profile(cls, value: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        raise ValueError("default_profile must be a string")

    @model_validator(mode="after")
    def _normalise(self) -> EngineSettingsModel:
        object.__setattr__(self, "plugin_args", _dedupe_preserve(self.plugin_args))
        object.__setattr__(self, "include", _dedupe_preserve(self.include))
        object.__setattr__(self, "exclude", _dedupe_preserve(self.exclude))
        normalised_profiles: dict[str, EngineProfileModel] = {}
        for key in sorted(self.profiles):
            profile = self.profiles[key]
            normalised_profiles[key.strip()] = profile
        object.__setattr__(self, "profiles", normalised_profiles)
        if self.default_profile and self.default_profile not in self.profiles:
            raise ValueError(f"default_profile '{self.default_profile}' is not defined in profiles")
        return self


class PathOverrideModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    engines: dict[str, EngineSettingsModel] = Field(default_factory=dict)
    active_profiles: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _normalise(self) -> PathOverrideModel:
        engines_map: dict[str, EngineSettingsModel] = {}
        for key in sorted(self.engines):
            engines_map[key.strip()] = self.engines[key]
        object.__setattr__(self, "engines", engines_map)
        profiles_map: dict[str, str] = {}
        for key, value in sorted(self.active_profiles.items()):
            profiles_map[key.strip()] = value.strip()
        object.__setattr__(self, "active_profiles", profiles_map)
        for engine, profile in profiles_map.items():
            settings = engines_map.get(engine)
            if settings and profile:
                # validation of profile presence happens when merged.
                continue
        return self


class AuditConfigModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    manifest_path: Path | None = None
    full_paths: list[str] | None = None
    max_depth: int | None = None
    max_files: int | None = None
    max_bytes: int | None = None
    skip_current: bool | None = None
    skip_full: bool | None = None
    fail_on: str | None = None
    dashboard_json: Path | None = None
    dashboard_markdown: Path | None = None
    dashboard_html: Path | None = None
    respect_gitignore: bool | None = None
    runners: list[str] | None = None
    plugin_args: dict[str, list[str]] = Field(default_factory=dict)
    engine_settings: dict[str, EngineSettingsModel] = Field(default_factory=dict, alias="engines")
    active_profiles: dict[str, str] = Field(default_factory=dict)

    @field_validator("full_paths", "runners", mode="before")
    @classmethod
    def _coerce_list(cls, value: object) -> list[str] | None:
        return _ensure_list(value)

    @field_validator("fail_on", mode="before")
    @classmethod
    def _lower_fail_on(cls, value: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"errors", "warnings", "never", "none", "any"}:
                return lowered
            raise ValueError("fail_on must be one of: errors, warnings, never")
        raise ValueError("fail_on must be a string")

    @field_validator("plugin_args", mode="before")
    @classmethod
    def _coerce_plugin_args(cls, value: object) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        if not isinstance(value, dict):
            return result
        value_dict: dict[object, object] = cast(dict[object, object], value)
        for key, raw in value_dict.items():
            key_str = str(key).strip()
            if not key_str:
                continue
            result[key_str] = _ensure_list(raw) or []
        return result

    @model_validator(mode="after")
    def _normalise(self) -> AuditConfigModel:
        # ensure deterministic order for plugin args
        normalised: dict[str, list[str]] = {}
        for key in sorted(self.plugin_args):
            values = _dedupe_preserve(self.plugin_args[key])
            normalised[key] = values
        object.__setattr__(self, "plugin_args", normalised)
        engines: dict[str, EngineSettingsModel] = {}
        for key in sorted(self.engine_settings):
            engines[key.strip()] = self.engine_settings[key]
        object.__setattr__(self, "engine_settings", engines)
        profiles: dict[str, str] = {}
        for key, value in sorted(self.active_profiles.items()):
            profiles[key.strip()] = value.strip()
        object.__setattr__(self, "active_profiles", profiles)
        for engine, profile in profiles.items():
            settings = self.engine_settings.get(engine)
            if settings and profile not in settings.profiles:
                raise ValueError(f"Unknown profile '{profile}' for engine '{engine}'")
        return self


class ConfigModel(BaseModel):
    config_version: int = Field(default=CONFIG_VERSION)
    audit: AuditConfigModel = Field(default_factory=AuditConfigModel)

    @model_validator(mode="after")
    def _check_version(self) -> ConfigModel:
        if self.config_version != CONFIG_VERSION:
            raise ValueError(
                f"Unsupported config_version {self.config_version}; expected {CONFIG_VERSION}"
            )
        return self


def _profile_from_model(model: EngineProfileModel) -> EngineProfile:
    payload = model.model_dump(mode="python")
    return EngineProfile(
        inherit=payload.get("inherit"),
        plugin_args=list(payload.get("plugin_args", [])),
        config_file=payload.get("config_file"),
        include=list(payload.get("include", [])),
        exclude=list(payload.get("exclude", [])),
    )


def _engine_settings_from_model(model: EngineSettingsModel) -> EngineSettings:
    payload = model.model_dump(mode="python")
    settings = EngineSettings(
        plugin_args=list(payload.get("plugin_args", [])),
        config_file=payload.get("config_file"),
        include=list(payload.get("include", [])),
        exclude=list(payload.get("exclude", [])),
        default_profile=payload.get("default_profile"),
    )
    profile_map: dict[str, EngineProfile] = {}
    for name, profile_model in model.profiles.items():
        profile_map[name] = _profile_from_model(profile_model)
    settings.profiles = profile_map
    return settings


def _path_override_from_model(path: Path, model: PathOverrideModel) -> PathOverride:
    override = PathOverride(path=path)
    override.engine_settings = {
        name: _engine_settings_from_model(settings_model)
        for name, settings_model in model.engines.items()
    }
    override.active_profiles = dict(model.active_profiles)
    return override


def _model_to_dataclass(model: AuditConfigModel) -> AuditConfig:
    data = model.model_dump(mode="python")
    engine_settings_models = model.engine_settings
    active_profiles = dict(model.active_profiles)
    data.pop("engine_settings", None)
    data.pop("active_profiles", None)
    audit = AuditConfig(**data)
    audit.engine_settings = {
        name: _engine_settings_from_model(settings_model)
        for name, settings_model in engine_settings_models.items()
    }
    audit.active_profiles = active_profiles
    return audit


def _resolve_path_fields(base_dir: Path, audit: AuditConfig) -> None:
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


def _discover_path_overrides(root: Path) -> list[PathOverride]:
    overrides: list[PathOverride] = []
    visited: set[Path] = set()
    for filename in FOLDER_CONFIG_FILENAMES:
        for config_path in sorted(root.rglob(filename)):
            if not config_path.is_file():
                continue
            directory = config_path.parent.resolve()
            try:
                raw = toml.loads(config_path.read_text(encoding="utf-8"))
            except Exception as exc:  # pragma: no cover - IO errors
                raise ValueError(f"Unable to read {config_path}: {exc}") from exc
            try:
                model = PathOverrideModel.model_validate(raw)
            except ValidationError as exc:
                raise ValueError(
                    f"Invalid typewiz directory override in {config_path}: {exc}"
                ) from exc
            override = _path_override_from_model(directory, model)
            overrides.append(override)
            visited.add(directory)
    overrides.sort(key=lambda item: (len(item.path.parts), item.path.as_posix()))
    return overrides


def load_config(explicit_path: Path | None = None) -> Config:
    search_order: list[Path] = []
    if explicit_path:
        search_order.append(explicit_path)
    else:
        search_order.append(Path("typewiz.toml"))
        search_order.append(Path(".typewiz.toml"))

    for candidate in search_order:
        if not candidate.exists():
            continue
        raw_map: dict[str, object] = toml.loads(candidate.read_text(encoding="utf-8"))
        tool_obj = raw_map.get("tool")
        if isinstance(tool_obj, dict):
            tool_section_any = cast(dict[str, object], tool_obj).get("typewiz")
            if isinstance(tool_section_any, dict):
                raw_map = cast(dict[str, object], tool_section_any)
        try:
            cfg_model = ConfigModel.model_validate(raw_map)
        except ValidationError as exc:  # pragma: no cover - configuration errors
            raise ValueError(f"Invalid typewiz configuration in {candidate}: {exc}") from exc
        audit = _model_to_dataclass(cfg_model.audit)
        root = candidate.parent.resolve()
        audit.path_overrides = _discover_path_overrides(root)
        _resolve_path_fields(root, audit)
        return Config(audit=audit)

    root = Path.cwd().resolve()
    cfg = Config()
    cfg.audit.runners = ["pyright", "mypy"]
    cfg.audit.path_overrides = _discover_path_overrides(root)
    _resolve_path_fields(root, cfg.audit)
    return cfg


FOLDER_CONFIG_FILENAMES: tuple[str, ...] = ("typewiz.dir.toml", ".typewizdir.toml")
