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

"""Configuration management for ratchetr.

This package provides configuration loading, validation, and model definitions
for ratchetr. It supports hierarchical configuration files with profile-based
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
