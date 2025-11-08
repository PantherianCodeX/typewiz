# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar, Final, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from typewiz.collections import dedupe_preserve
from typewiz.config.validation import require_non_negative_int
from typewiz.core.model_types import FailOnPolicy, SeverityLevel, SignaturePolicy
from typewiz.core.type_aliases import EngineName, ProfileName, RunId, RunnerName
from typewiz.exceptions import TypewizValidationError

CONFIG_VERSION: Final[int] = 0
FAIL_ON_ALLOWED_VALUES: Final[tuple[str, ...]] = tuple(policy.value for policy in FailOnPolicy)


class ConfigValidationError(TypewizValidationError):
    """Raised when configuration data contains invalid values."""


class ConfigFieldTypeError(ConfigValidationError):
    """Raised when a configuration field has an invalid type."""

    def __init__(self, field: str) -> None:
        self.field = field
        super().__init__(f"{field} must be a string")


class ConfigFieldChoiceError(ConfigValidationError):
    """Raised when a configuration field is provided with an unsupported value."""

    def __init__(self, field: str, allowed: tuple[str, ...]) -> None:
        self.field = field
        self.allowed = allowed
        allowed_text = ", ".join(sorted(allowed))
        super().__init__(f"{field} must be one of: {allowed_text}")


class UndefinedDefaultProfileError(ConfigValidationError):
    """Raised when a default profile references an undefined profile name."""

    def __init__(self, profile: str) -> None:
        self.profile = profile
        super().__init__(f"default_profile '{profile}' is not defined in profiles")


class UnknownEngineProfileError(ConfigValidationError):
    """Raised when a path override references an unknown engine profile."""

    def __init__(self, engine: str, profile: str) -> None:
        self.engine = engine
        self.profile = profile
        super().__init__(f"Unknown profile '{profile}' for engine '{engine}'")


class UnsupportedConfigVersionError(ConfigValidationError):
    """Raised when a configuration file declares an unsupported schema version."""

    def __init__(self, provided: int, expected: int) -> None:
        self.provided = provided
        self.expected = expected
        super().__init__(f"Unsupported config_version {provided}; expected {expected}")


class ConfigReadError(ConfigValidationError):
    """Raised when a configuration file cannot be read from disk."""

    def __init__(self, path: Path, error: Exception) -> None:
        self.path = path
        self.error = error
        super().__init__(f"Unable to read {path}: {error}")


class DirectoryOverrideValidationError(ConfigValidationError):
    """Raised when a directory override manifest fails validation."""

    def __init__(self, path: Path, error: Exception) -> None:
        self.path = path
        self.error = error
        super().__init__(f"Invalid typewiz directory override in {path}: {error}")


class InvalidConfigFileError(ConfigValidationError):
    """Raised when the root configuration file fails validation."""

    def __init__(self, path: Path, error: Exception) -> None:
        self.path = path
        self.error = error
        super().__init__(f"Invalid typewiz configuration in {path}: {error}")


def _default_list_str() -> list[str]:
    return []


@dataclass(slots=True)
class EngineProfile:
    inherit: ProfileName | None = None
    plugin_args: list[str] = field(default_factory=_default_list_str)
    config_file: Path | None = None
    include: list[str] = field(default_factory=_default_list_str)
    exclude: list[str] = field(default_factory=_default_list_str)


def _default_dict_profile_engineprofile() -> dict[ProfileName, EngineProfile]:
    return {}


@dataclass(slots=True)
class EngineSettings:
    plugin_args: list[str] = field(default_factory=_default_list_str)
    config_file: Path | None = None
    include: list[str] = field(default_factory=_default_list_str)
    exclude: list[str] = field(default_factory=_default_list_str)
    default_profile: ProfileName | None = None
    profiles: dict[ProfileName, EngineProfile] = field(
        default_factory=_default_dict_profile_engineprofile,
    )


def _default_dict_str_liststr() -> dict[EngineName, list[str]]:
    return {}


def _default_dict_str_enginesettings() -> dict[EngineName, EngineSettings]:
    return {}


def _default_dict_engine_profile() -> dict[EngineName, ProfileName]:
    return {}


def _default_list_path_override() -> list[PathOverride]:
    return []


def _default_dict_str_int() -> dict[str, int]:
    return {}


def _default_ratchet_runs() -> list[RunId]:
    return cast(list[RunId], [])


def _default_ratchet_severity_levels() -> list[SeverityLevel]:
    return [SeverityLevel.ERROR, SeverityLevel.WARNING]


@dataclass(slots=True)
class AuditConfig:
    manifest_path: Path | None = None
    full_paths: list[str] | None = None
    max_depth: int | None = None
    max_files: int | None = None
    max_bytes: int | None = None
    skip_current: bool | None = None
    skip_full: bool | None = None
    fail_on: FailOnPolicy | None = None
    hash_workers: int | Literal["auto"] | None = None
    dashboard_json: Path | None = None
    dashboard_markdown: Path | None = None
    dashboard_html: Path | None = None
    respect_gitignore: bool | None = None
    runners: list[RunnerName] | None = None
    plugin_args: dict[EngineName, list[str]] = field(default_factory=_default_dict_str_liststr)
    engine_settings: dict[EngineName, EngineSettings] = field(
        default_factory=_default_dict_str_enginesettings,
    )
    active_profiles: dict[EngineName, ProfileName] = field(
        default_factory=_default_dict_engine_profile,
    )
    path_overrides: list[PathOverride] = field(default_factory=_default_list_path_override)

    def __post_init__(self) -> None:
        self.plugin_args = {
            EngineName(name): list(values) for name, values in self.plugin_args.items()
        }
        self.engine_settings = {
            EngineName(name): value for name, value in self.engine_settings.items()
        }
        self.active_profiles = {
            EngineName(name): ProfileName(profile) for name, profile in self.active_profiles.items()
        }
        if self.runners is not None:
            self.runners = [RunnerName(EngineName(name)) for name in self.runners]


@dataclass(slots=True)
class Config:
    audit: AuditConfig = field(default_factory=AuditConfig)
    ratchet: RatchetConfig = field(default_factory=lambda: RatchetConfig())


@dataclass(slots=True)
class PathOverride:
    path: Path
    engine_settings: dict[EngineName, EngineSettings] = field(
        default_factory=_default_dict_str_enginesettings,
    )
    active_profiles: dict[EngineName, ProfileName] = field(
        default_factory=_default_dict_engine_profile,
    )

    def __post_init__(self) -> None:
        self.engine_settings = {
            EngineName(name): value for name, value in self.engine_settings.items()
        }
        self.active_profiles = {
            EngineName(name): ProfileName(profile) for name, profile in self.active_profiles.items()
        }


@dataclass(slots=True)
class RatchetConfig:
    manifest_path: Path | None = None
    output_path: Path | None = None
    runs: list[RunId] = field(default_factory=_default_ratchet_runs)
    severities: list[SeverityLevel] = field(default_factory=_default_ratchet_severity_levels)
    targets: dict[str, int] = field(default_factory=_default_dict_str_int)
    signature: SignaturePolicy = SignaturePolicy.FAIL
    limit: int | None = None
    summary_only: bool = False

    def __post_init__(self) -> None:
        self.runs = [RunId(str(value).strip()) for value in self.runs if str(value).strip()]


def ensure_list(value: object | None) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if not isinstance(value, Iterable):
        return []
    result: list[str] = []
    for item in cast("Iterable[object]", value):
        if isinstance(item, str):
            stripped = item.strip()
            if stripped:
                result.append(stripped)
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
        return ensure_list(value) or []

    @field_validator("inherit", mode="before")
    @classmethod
    def _strip_inherit(cls, value: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        raise ConfigFieldTypeError("inherit")

    @model_validator(mode="after")
    def _normalise(self) -> EngineProfileModel:
        object.__setattr__(self, "plugin_args", dedupe_preserve(self.plugin_args))
        object.__setattr__(self, "include", dedupe_preserve(self.include))
        object.__setattr__(self, "exclude", dedupe_preserve(self.exclude))
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
        return ensure_list(value) or []

    @field_validator("default_profile", mode="before")
    @classmethod
    def _strip_default_profile(cls, value: object) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        raise ConfigFieldTypeError("default_profile")

    @model_validator(mode="after")
    def _normalise(self) -> EngineSettingsModel:
        object.__setattr__(self, "plugin_args", dedupe_preserve(self.plugin_args))
        object.__setattr__(self, "include", dedupe_preserve(self.include))
        object.__setattr__(self, "exclude", dedupe_preserve(self.exclude))
        normalised_profiles: dict[str, EngineProfileModel] = {}
        for key in sorted(self.profiles):
            profile = self.profiles[key]
            normalised_profiles[key.strip()] = profile
        object.__setattr__(self, "profiles", normalised_profiles)
        if self.default_profile and self.default_profile not in self.profiles:
            raise UndefinedDefaultProfileError(self.default_profile)
        return self


class PathOverrideModel(BaseModel):
    model_config: ClassVar[ConfigDict] = ConfigDict(populate_by_name=True)
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
    model_config: ClassVar[ConfigDict] = ConfigDict(populate_by_name=True)
    manifest_path: Path | None = None
    full_paths: list[str] | None = None
    max_depth: int | None = None
    max_files: int | None = None
    max_bytes: int | None = None
    skip_current: bool | None = None
    skip_full: bool | None = None
    fail_on: FailOnPolicy | None = None
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
        return ensure_list(value)

    @field_validator("max_depth", "max_files", "max_bytes", mode="before")
    @classmethod
    def _validate_limits(cls, value: object, info: ValidationInfo) -> int | None:
        if value is None:
            return None
        context = info.field_name or "value"
        return require_non_negative_int(value, context=context)

    @field_validator("fail_on", mode="before")
    @classmethod
    def _normalise_fail_on(cls, value: object) -> FailOnPolicy | None:
        if value is None:
            return None
        if isinstance(value, FailOnPolicy):
            return value
        if isinstance(value, str):
            try:
                return FailOnPolicy.from_str(value)
            except ValueError as exc:
                raise ConfigFieldChoiceError("fail_on", FAIL_ON_ALLOWED_VALUES) from exc
        raise ConfigFieldTypeError("fail_on")

    @field_validator("plugin_args", mode="before")
    @classmethod
    def _coerce_plugin_args(cls, value: object) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {}
        if not isinstance(value, dict):
            return result
        value_dict: dict[object, object] = cast("dict[object, object]", value)
        for key, raw in value_dict.items():
            key_str = str(key).strip()
            if not key_str:
                continue
            result[key_str] = ensure_list(raw) or []
        return result

    @model_validator(mode="after")
    def _normalise(self) -> AuditConfigModel:
        # ensure deterministic order for plugin args
        normalised: dict[str, list[str]] = {}
        for key in sorted(self.plugin_args):
            values = dedupe_preserve(self.plugin_args[key])
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
                raise UnknownEngineProfileError(engine, profile)
        if self.runners:
            object.__setattr__(self, "runners", dedupe_preserve(self.runners))
        return self


class RatchetConfigModel(BaseModel):
    manifest_path: Path | None = None
    output_path: Path | None = None

    runs: list[RunId] = Field(default_factory=_default_ratchet_runs)
    severities: list[SeverityLevel] = Field(default_factory=_default_ratchet_severity_levels)
    targets: dict[str, int] = Field(default_factory=dict)
    signature: SignaturePolicy = Field(default=SignaturePolicy.FAIL)
    limit: int | None = None
    summary_only: bool = False

    @field_validator("runs", mode="before")
    @classmethod
    def _coerce_runs(cls, value: object) -> list[RunId]:
        runs = ensure_list(value) or []
        return [RunId(token) for token in runs]

    @field_validator("severities", mode="before")
    @classmethod
    def _coerce_severities(cls, value: object) -> list[SeverityLevel]:
        severities = ensure_list(value)
        if not severities:
            return _default_ratchet_severity_levels()
        result = [SeverityLevel.from_str(token) for token in severities]
        return result or _default_ratchet_severity_levels()

    @field_validator("targets", mode="before")
    @classmethod
    def _coerce_targets(cls, value: object) -> dict[str, int]:
        if not isinstance(value, Mapping):
            return {}
        result: dict[str, int] = {}
        for key, raw in cast("Mapping[object, object]", value).items():
            key_str = str(key).strip()
            if not key_str:
                continue
            candidate: int | None
            if isinstance(raw, bool):
                candidate = int(raw)
            elif isinstance(raw, (int, float)):
                candidate = int(raw)
            elif isinstance(raw, str):
                try:
                    candidate = int(raw.strip())
                except ValueError:
                    candidate = None
            else:
                candidate = None
            if candidate is None:
                continue
            result[key_str] = max(candidate, 0)
        return result

    @field_validator("signature", mode="before")
    @classmethod
    def _normalise_signature(cls, value: object) -> SignaturePolicy:
        if value is None:
            return SignaturePolicy.FAIL
        if isinstance(value, SignaturePolicy):
            return value
        if isinstance(value, str):
            try:
                return SignaturePolicy.from_str(value)
            except ValueError as exc:
                raise ConfigFieldChoiceError(
                    "ratchet.signature",
                    tuple(policy.value for policy in SignaturePolicy),
                ) from exc
        raise ConfigFieldTypeError("ratchet.signature")


class ConfigModel(BaseModel):
    config_version: int = Field(default=CONFIG_VERSION)
    audit: AuditConfigModel = Field(default_factory=AuditConfigModel)
    ratchet: RatchetConfigModel = Field(default_factory=RatchetConfigModel)

    @model_validator(mode="after")
    def _check_version(self) -> ConfigModel:
        if self.config_version != CONFIG_VERSION:
            raise UnsupportedConfigVersionError(self.config_version, CONFIG_VERSION)
        return self


def _profile_name_or_none(value: str | ProfileName | None) -> ProfileName | None:
    if value is None:
        return None
    return ProfileName(value)


def _profile_from_model(model: EngineProfileModel) -> EngineProfile:
    payload = model.model_dump(mode="python")
    return EngineProfile(
        inherit=_profile_name_or_none(payload.get("inherit")),
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
        default_profile=_profile_name_or_none(payload.get("default_profile")),
    )
    profile_map: dict[ProfileName, EngineProfile] = {}
    for name, profile_model in model.profiles.items():
        profile_map[ProfileName(name)] = _profile_from_model(profile_model)
    settings.profiles = profile_map
    return settings


def path_override_from_model(path: Path, model: PathOverrideModel) -> PathOverride:
    override = PathOverride(path=path)
    override.engine_settings = {
        EngineName(name): _engine_settings_from_model(settings_model)
        for name, settings_model in model.engines.items()
    }
    override.active_profiles = {
        EngineName(name): ProfileName(profile)
        for name, profile in model.active_profiles.items()
        if profile
    }
    return override


def model_to_dataclass(model: AuditConfigModel) -> AuditConfig:
    data = model.model_dump(mode="python")
    engine_settings_models = model.engine_settings
    plugin_args_raw: dict[str, list[str]] = data.get("plugin_args", {}) or {}
    data["plugin_args"] = {
        EngineName(name): list(values) for name, values in plugin_args_raw.items()
    }
    active_profiles = {
        EngineName(name): ProfileName(profile)
        for name, profile in model.active_profiles.items()
        if profile
    }
    data.pop("engine_settings", None)
    data.pop("active_profiles", None)
    audit = AuditConfig(**data)
    audit.engine_settings = {
        EngineName(name): _engine_settings_from_model(settings_model)
        for name, settings_model in engine_settings_models.items()
    }
    audit.active_profiles = active_profiles
    return audit


def ratchet_from_model(model: RatchetConfigModel) -> RatchetConfig:
    payload = model.model_dump(mode="python")
    payload["runs"] = [RunId(item) for item in cast("Sequence[str]", payload.get("runs", []))]
    payload["severities"] = [
        SeverityLevel.from_str(item)
        for item in cast("Sequence[str]", payload.get("severities", []))
    ]
    return RatchetConfig(**payload)
