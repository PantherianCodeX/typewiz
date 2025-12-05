# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Configuration management for TypeWiz.

This package provides configuration loading, validation, and model definitions
for TypeWiz. It supports hierarchical configuration files with profile-based
engine settings and directory-level overrides.
"""

from __future__ import annotations

from .loader import load_config, resolve_path_fields
from .models import (
    AuditConfig,
    AuditConfigModel,
    Config,
    ConfigFieldChoiceError,
    ConfigFieldTypeError,
    ConfigModel,
    ConfigReadError,
    ConfigValidationError,
    DirectoryOverrideValidationError,
    EngineProfile,
    EngineProfileModel,
    EngineSettings,
    EngineSettingsModel,
    InvalidConfigFileError,
    PathOverride,
    PathOverrideModel,
    RatchetConfig,
    RatchetConfigModel,
    UndefinedDefaultProfileError,
    UnknownEngineProfileError,
    UnsupportedConfigVersionError,
    ensure_list,
)

__all__ = [
    "AuditConfig",
    "AuditConfigModel",
    "Config",
    "ConfigFieldChoiceError",
    "ConfigFieldTypeError",
    "ConfigModel",
    "ConfigReadError",
    "ConfigValidationError",
    "DirectoryOverrideValidationError",
    "EngineProfile",
    "EngineProfileModel",
    "EngineSettings",
    "EngineSettingsModel",
    "InvalidConfigFileError",
    "PathOverride",
    "PathOverrideModel",
    "RatchetConfig",
    "RatchetConfigModel",
    "UndefinedDefaultProfileError",
    "UnknownEngineProfileError",
    "UnsupportedConfigVersionError",
    "ensure_list",
    "load_config",
    "resolve_path_fields",
]
