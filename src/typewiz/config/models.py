# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Configuration models and validation for Typewiz.

This module defines the data models for Typewiz configuration, including both
Pydantic models for loading and validation from TOML files, and dataclass models
for runtime use. It provides schema validation, type coercion, and conversion
functions to transform configuration data into strongly-typed structures.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar, Final, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

from typewiz.collections import dedupe_preserve
from typewiz.config.validation import require_non_negative_int
from typewiz.core.model_types import FailOnPolicy, SeverityLevel, SignaturePolicy
from typewiz.core.type_aliases import EngineName, ProfileName, RunId, RunnerName
from typewiz.exceptions import TypewizValidationError

if TYPE_CHECKING:
    from pathlib import Path

CONFIG_VERSION: Final[int] = 0
FAIL_ON_ALLOWED_VALUES: Final[tuple[str, ...]] = tuple(policy.value for policy in FailOnPolicy)


class ConfigValidationError(TypewizValidationError):
    """Raised when configuration data contains invalid values."""


class ConfigFieldTypeError(ConfigValidationError):
    """Raised when a configuration field has an invalid type."""

    def __init__(self, field: str) -> None:
        """Initialize the exception with the field name that has an invalid type.

        Args:
            field: The name of the configuration field with an invalid type.
        """
        self.field = field
        super().__init__(f"{field} must be a string")


class ConfigFieldChoiceError(ConfigValidationError):
    """Raised when a configuration field is provided with an unsupported value."""

    def __init__(self, field: str, allowed: tuple[str, ...]) -> None:
        """Initialize the exception with the field name and allowed values.

        Args:
            field: The name of the configuration field with an invalid value.
            allowed: Tuple of allowed values for this field.
        """
        self.field = field
        self.allowed = allowed
        allowed_text = ", ".join(sorted(allowed))
        super().__init__(f"{field} must be one of: {allowed_text}")


class UndefinedDefaultProfileError(ConfigValidationError):
    """Raised when a default profile references an undefined profile name."""

    def __init__(self, profile: str) -> None:
        """Initialize the exception with the undefined profile name.

        Args:
            profile: The name of the profile that was referenced but not defined.
        """
        self.profile = profile
        super().__init__(f"default_profile '{profile}' is not defined in profiles")


class UnknownEngineProfileError(ConfigValidationError):
    """Raised when a path override references an unknown engine profile."""

    def __init__(self, engine: str, profile: str) -> None:
        """Initialize the exception with the engine and unknown profile name.

        Args:
            engine: The name of the engine for which the profile is undefined.
            profile: The name of the profile that was referenced but not defined.
        """
        self.engine = engine
        self.profile = profile
        super().__init__(f"Unknown profile '{profile}' for engine '{engine}'")


class UnsupportedConfigVersionError(ConfigValidationError):
    """Raised when a configuration file declares an unsupported schema version."""

    def __init__(self, provided: int, expected: int) -> None:
        """Initialize the exception with version information.

        Args:
            provided: The config_version value provided in the configuration file.
            expected: The config_version value expected by this version of Typewiz.
        """
        self.provided = provided
        self.expected = expected
        super().__init__(f"Unsupported config_version {provided}; expected {expected}")


class ConfigReadError(ConfigValidationError):
    """Raised when a configuration file cannot be read from disk."""

    def __init__(self, path: Path, error: Exception) -> None:
        """Initialize the exception with file path and underlying error.

        Args:
            path: The path to the configuration file that could not be read.
            error: The underlying exception that caused the read failure.
        """
        self.path = path
        self.error = error
        super().__init__(f"Unable to read {path}: {error}")


class DirectoryOverrideValidationError(ConfigValidationError):
    """Raised when a directory override manifest fails validation."""

    def __init__(self, path: Path, error: Exception) -> None:
        """Initialize the exception with directory override path and validation error.

        Args:
            path: The path to the directory override file that failed validation.
            error: The underlying validation exception.
        """
        self.path = path
        self.error = error
        super().__init__(f"Invalid typewiz directory override in {path}: {error}")


class InvalidConfigFileError(ConfigValidationError):
    """Raised when the root configuration file fails validation."""

    def __init__(self, path: Path, error: Exception) -> None:
        """Initialize the exception with configuration file path and validation error.

        Args:
            path: The path to the configuration file that failed validation.
            error: The underlying validation exception.
        """
        self.path = path
        self.error = error
        super().__init__(f"Invalid typewiz configuration in {path}: {error}")


def _default_list_str() -> list[str]:
    return []


@dataclass(slots=True)
class EngineProfile:
    """Configuration profile for customizing type checker engine behavior.

    Profiles allow defining reusable sets of engine configuration options that can
    be selected for specific directories or use cases. Profiles support inheritance
    from other profiles to enable layering of configuration.

    Attributes:
        inherit: Optional name of another profile to inherit settings from.
        plugin_args: Additional command-line arguments to pass to the engine.
        config_file: Optional path to an engine-specific configuration file.
        include: List of glob patterns for files to include in type checking.
        exclude: List of glob patterns for files to exclude from type checking.
    """

    inherit: ProfileName | None = None
    plugin_args: list[str] = field(default_factory=_default_list_str)
    config_file: Path | None = None
    include: list[str] = field(default_factory=_default_list_str)
    exclude: list[str] = field(default_factory=_default_list_str)


def _default_dict_profile_engineprofile() -> dict[ProfileName, EngineProfile]:
    return {}


@dataclass(slots=True)
class EngineSettings:
    """Configuration settings for a type checker engine.

    This class defines all configuration options for a specific type checker engine
    (e.g., mypy, pyright), including base settings and named profiles. Settings can
    be applied globally or overridden for specific directories.

    Attributes:
        plugin_args: Additional command-line arguments to pass to the engine.
        config_file: Optional path to an engine-specific configuration file.
        include: List of glob patterns for files to include in type checking.
        exclude: List of glob patterns for files to exclude from type checking.
        default_profile: Name of the profile to use by default if no profile is
            explicitly selected.
        profiles: Dictionary mapping profile names to EngineProfile configurations.
    """

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
    return cast("list[RunId]", [])


def _default_ratchet_severity_levels() -> list[SeverityLevel]:
    return [SeverityLevel.ERROR, SeverityLevel.WARNING]


@dataclass(slots=True)
class AuditConfig:
    """Configuration settings for type checking audits.

    This class contains all configuration options for running type checking audits,
    including file discovery options, engine settings, output formats, and path-specific
    overrides.

    Attributes:
        manifest_path: Optional path to save the audit manifest file.
        full_paths: List of specific file paths to audit. If provided, only these
            files are checked.
        max_depth: Maximum directory depth for recursive file discovery.
        max_files: Maximum number of files to include in the audit.
        max_bytes: Maximum total size in bytes of files to include in the audit.
        skip_current: Whether to skip files in the current directory.
        skip_full: Whether to skip the full audit and only check changed files.
        fail_on: Policy for when the audit should fail (e.g., on errors, warnings).
        hash_workers: Number of workers for parallel file hashing, or "auto" to
            determine automatically.
        dashboard_json: Optional path to save JSON format dashboard output.
        dashboard_markdown: Optional path to save Markdown format dashboard output.
        dashboard_html: Optional path to save HTML format dashboard output.
        respect_gitignore: Whether to respect .gitignore patterns during file discovery.
        runners: List of type checker engines to run (e.g., mypy, pyright).
        plugin_args: Additional command-line arguments for each engine.
        engine_settings: Configuration settings for each engine.
        active_profiles: Currently active profile for each engine.
        path_overrides: List of directory-specific configuration overrides.
    """

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
        """Normalize configuration data after initialization."""
        self.plugin_args = {EngineName(name): list(values) for name, values in self.plugin_args.items()}
        self.engine_settings = {EngineName(name): value for name, value in self.engine_settings.items()}
        self.active_profiles = {
            EngineName(name): ProfileName(profile) for name, profile in self.active_profiles.items()
        }
        if self.runners is not None:
            self.runners = [RunnerName(EngineName(name)) for name in self.runners]


@dataclass(slots=True)
class Config:
    """Top-level configuration for Typewiz.

    This is the root configuration object that contains all settings for both
    audit and ratchet operations.

    Attributes:
        audit: Configuration settings for type checking audits.
        ratchet: Configuration settings for ratcheting (progressive type coverage).
    """

    audit: AuditConfig = field(default_factory=AuditConfig)
    ratchet: RatchetConfig = field(default_factory=lambda: RatchetConfig())  # noqa: PLW0108


@dataclass(slots=True)
class PathOverride:
    """Directory-specific configuration overrides.

    This class represents configuration settings that apply to a specific directory
    and its subdirectories, allowing different type checking configurations for
    different parts of a codebase.

    Attributes:
        path: The directory path this override applies to.
        engine_settings: Engine-specific configuration settings for this directory.
        active_profiles: Active profile for each engine in this directory.
    """

    path: Path
    engine_settings: dict[EngineName, EngineSettings] = field(
        default_factory=_default_dict_str_enginesettings,
    )
    active_profiles: dict[EngineName, ProfileName] = field(
        default_factory=_default_dict_engine_profile,
    )

    def __post_init__(self) -> None:
        """Normalize configuration data after initialization."""
        self.engine_settings = {EngineName(name): value for name, value in self.engine_settings.items()}
        self.active_profiles = {
            EngineName(name): ProfileName(profile) for name, profile in self.active_profiles.items()
        }


@dataclass(slots=True)
class RatchetConfig:
    """Configuration settings for ratcheting (progressive type coverage).

    Ratcheting allows progressive improvement of type coverage by setting targets
    and tracking progress over time. This configuration controls which runs to
    compare, what severity levels to track, and how to handle signature coverage.

    Attributes:
        manifest_path: Optional path to the manifest file to use for ratcheting.
        output_path: Optional path to save ratchet output.
        runs: List of run IDs to include in ratchet comparisons. Empty list means
            use all available runs.
        severities: List of severity levels to include in ratchet tracking
            (defaults to ERROR and WARNING).
        targets: Dictionary mapping metric names to target values for ratcheting.
        signature: Policy for handling function signature coverage (fail, warn, or ignore).
        limit: Optional limit on the number of issues to display.
        summary_only: Whether to show only summary information without detailed issues.
    """

    manifest_path: Path | None = None
    output_path: Path | None = None
    runs: list[RunId] = field(default_factory=_default_ratchet_runs)
    severities: list[SeverityLevel] = field(default_factory=_default_ratchet_severity_levels)
    targets: dict[str, int] = field(default_factory=_default_dict_str_int)
    signature: SignaturePolicy = SignaturePolicy.FAIL
    limit: int | None = None
    summary_only: bool = False

    def __post_init__(self) -> None:
        """Normalize run IDs after initialization."""
        self.runs = [RunId(str(value).strip()) for value in self.runs if str(value).strip()]


def ensure_list(value: object | None) -> list[str] | None:
    """Convert various input types to a list of strings, or None.

    This function normalizes various input formats (strings, iterables) into a
    list of strings, handling whitespace trimming and filtering empty values.
    If the input is None, returns None.

    Args:
        value: The input value to convert. Can be None, a string, or an iterable.

    Returns:
        A list of non-empty strings, or None if the input was None. Returns an
        empty list if the input was an empty string or contained no valid items.
    """
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
    """Pydantic model for validating engine profile configuration from TOML.

    This model is used to validate and load engine profile configuration data from
    TOML files. After validation, it is converted to an EngineProfile dataclass for
    runtime use.

    Attributes:
        inherit: Optional name of another profile to inherit settings from.
        plugin_args: Additional command-line arguments to pass to the engine.
        config_file: Optional path to an engine-specific configuration file.
        include: List of glob patterns for files to include in type checking.
        exclude: List of glob patterns for files to exclude from type checking.
    """

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
        msg = "inherit"
        raise ConfigFieldTypeError(msg)

    @model_validator(mode="after")
    def _normalise(self) -> EngineProfileModel:
        self.plugin_args = dedupe_preserve(self.plugin_args)
        self.include = dedupe_preserve(self.include)
        self.exclude = dedupe_preserve(self.exclude)
        return self


class EngineSettingsModel(BaseModel):
    """Pydantic model for validating engine settings configuration from TOML.

    This model is used to validate and load engine settings configuration data from
    TOML files. After validation, it is converted to an EngineSettings dataclass for
    runtime use.

    Attributes:
        plugin_args: Additional command-line arguments to pass to the engine.
        config_file: Optional path to an engine-specific configuration file.
        include: List of glob patterns for files to include in type checking.
        exclude: List of glob patterns for files to exclude from type checking.
        default_profile: Name of the profile to use by default if no profile is
            explicitly selected.
        profiles: Dictionary mapping profile names to EngineProfileModel configurations.
    """

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
        msg = "default_profile"
        raise ConfigFieldTypeError(msg)

    @model_validator(mode="after")
    def _normalise(self) -> EngineSettingsModel:
        self.plugin_args = dedupe_preserve(self.plugin_args)
        self.include = dedupe_preserve(self.include)
        self.exclude = dedupe_preserve(self.exclude)
        normalised_profiles: dict[str, EngineProfileModel] = {}
        for key in sorted(self.profiles):
            profile = self.profiles[key]
            normalised_profiles[key.strip()] = profile
        self.profiles = normalised_profiles
        if self.default_profile and self.default_profile not in self.profiles:
            raise UndefinedDefaultProfileError(self.default_profile)
        return self


class PathOverrideModel(BaseModel):
    """Pydantic model for validating directory-specific configuration overrides from TOML.

    This model is used to validate and load directory override configuration data from
    TOML files (typewiz.dir.toml, .typewizdir.toml). After validation, it is converted
    to a PathOverride dataclass for runtime use.

    Attributes:
        engines: Dictionary mapping engine names to EngineSettingsModel configurations.
        active_profiles: Dictionary mapping engine names to active profile names.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(populate_by_name=True)
    engines: dict[str, EngineSettingsModel] = Field(default_factory=dict)
    active_profiles: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _normalise(self) -> PathOverrideModel:
        engines_map: dict[str, EngineSettingsModel] = {}
        for key in sorted(self.engines):
            engines_map[key.strip()] = self.engines[key]
        self.engines = engines_map
        profiles_map: dict[str, str] = {}
        for key, value in sorted(self.active_profiles.items()):
            profiles_map[key.strip()] = value.strip()
        self.active_profiles = profiles_map
        for engine, profile in profiles_map.items():
            settings = engines_map.get(engine)
            if settings and profile:
                # validation of profile presence happens when merged.
                continue
        return self


class AuditConfigModel(BaseModel):
    """Pydantic model for validating audit configuration from TOML.

    This model is used to validate and load audit configuration data from TOML files.
    After validation, it is converted to an AuditConfig dataclass for runtime use.

    Attributes:
        manifest_path: Optional path to save the audit manifest file.
        full_paths: List of specific file paths to audit.
        max_depth: Maximum directory depth for recursive file discovery.
        max_files: Maximum number of files to include in the audit.
        max_bytes: Maximum total size in bytes of files to include in the audit.
        skip_current: Whether to skip files in the current directory.
        skip_full: Whether to skip the full audit and only check changed files.
        fail_on: Policy for when the audit should fail.
        dashboard_json: Optional path to save JSON format dashboard output.
        dashboard_markdown: Optional path to save Markdown format dashboard output.
        dashboard_html: Optional path to save HTML format dashboard output.
        respect_gitignore: Whether to respect .gitignore patterns during file discovery.
        runners: List of type checker engines to run.
        plugin_args: Additional command-line arguments for each engine.
        engine_settings: Configuration settings for each engine (aliased as "engines").
        active_profiles: Currently active profile for each engine.
    """

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
                msg = "fail_on"
                raise ConfigFieldChoiceError(msg, FAIL_ON_ALLOWED_VALUES) from exc
        msg = "fail_on"
        raise ConfigFieldTypeError(msg)

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
        self.plugin_args = normalised
        engines: dict[str, EngineSettingsModel] = {}
        for key in sorted(self.engine_settings):
            engines[key.strip()] = self.engine_settings[key]
        self.engine_settings = engines
        profiles: dict[str, str] = {}
        for key, value in sorted(self.active_profiles.items()):
            profiles[key.strip()] = value.strip()
        self.active_profiles = profiles
        for engine, profile in profiles.items():
            settings = self.engine_settings.get(engine)
            if settings and profile not in settings.profiles:
                raise UnknownEngineProfileError(engine, profile)
        if self.runners:
            self.runners = dedupe_preserve(self.runners)
        return self


class RatchetConfigModel(BaseModel):
    """Pydantic model for validating ratchet configuration from TOML.

    This model is used to validate and load ratchet configuration data from TOML files.
    After validation, it is converted to a RatchetConfig dataclass for runtime use.

    Attributes:
        manifest_path: Optional path to the manifest file to use for ratcheting.
        output_path: Optional path to save ratchet output.
        runs: List of run IDs to include in ratchet comparisons.
        severities: List of severity levels to include in ratchet tracking.
        targets: Dictionary mapping metric names to target values for ratcheting.
        signature: Policy for handling function signature coverage.
        limit: Optional limit on the number of issues to display.
        summary_only: Whether to show only summary information without detailed issues.
    """

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
            if isinstance(raw, (bool, int, float)):
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
                msg = "ratchet.signature"
                raise ConfigFieldChoiceError(
                    msg,
                    tuple(policy.value for policy in SignaturePolicy),
                ) from exc
        msg = "ratchet.signature"
        raise ConfigFieldTypeError(msg)


class ConfigModel(BaseModel):
    """Pydantic model for validating the top-level Typewiz configuration from TOML.

    This is the root configuration model that validates the entire configuration file
    structure. After validation, it is converted to a Config dataclass for runtime use.

    Attributes:
        config_version: Schema version number for the configuration file.
        audit: Audit configuration settings.
        ratchet: Ratchet configuration settings.
    """

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
    """Convert a PathOverrideModel to a PathOverride dataclass.

    This function transforms a validated Pydantic model into a runtime dataclass,
    converting all nested models and normalizing engine names and profile names.

    Args:
        path: The directory path this override applies to.
        model: The validated PathOverrideModel from TOML parsing.

    Returns:
        A PathOverride dataclass ready for runtime use.
    """
    override = PathOverride(path=path)
    override.engine_settings = {
        EngineName(name): _engine_settings_from_model(settings_model) for name, settings_model in model.engines.items()
    }
    override.active_profiles = {
        EngineName(name): ProfileName(profile) for name, profile in model.active_profiles.items() if profile
    }
    return override


def model_to_dataclass(model: AuditConfigModel) -> AuditConfig:
    """Convert an AuditConfigModel to an AuditConfig dataclass.

    This function transforms a validated Pydantic model into a runtime dataclass,
    converting all nested models, normalizing engine names and profile names, and
    ensuring all configuration data is ready for runtime use.

    Args:
        model: The validated AuditConfigModel from TOML parsing.

    Returns:
        An AuditConfig dataclass ready for runtime use with all paths and settings
        properly configured.
    """
    data = model.model_dump(mode="python")
    engine_settings_models = model.engine_settings
    plugin_args_raw: dict[str, list[str]] = data.get("plugin_args", {}) or {}
    data["plugin_args"] = {EngineName(name): list(values) for name, values in plugin_args_raw.items()}
    active_profiles = {
        EngineName(name): ProfileName(profile) for name, profile in model.active_profiles.items() if profile
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
    """Convert a RatchetConfigModel to a RatchetConfig dataclass.

    This function transforms a validated Pydantic model into a runtime dataclass,
    converting run IDs and severity levels to their appropriate types.

    Args:
        model: The validated RatchetConfigModel from TOML parsing.

    Returns:
        A RatchetConfig dataclass ready for runtime use.
    """
    payload = model.model_dump(mode="python")
    payload["runs"] = [RunId(item) for item in cast("Sequence[str]", payload.get("runs", []))]
    payload["severities"] = [
        SeverityLevel.from_str(item) for item in cast("Sequence[str]", payload.get("severities", []))
    ]
    return RatchetConfig(**payload)
