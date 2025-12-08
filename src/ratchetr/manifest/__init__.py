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

"""Manifest generation and validation for ratchetr typing audits.

This package provides the core functionality for creating, loading, and validating typing audit manifests. Manifests
contain aggregated diagnostic information from type checking tools (mypy, pyright, etc.) and support structured analysis
of typing health across projects.

Key components:
    - ManifestBuilder: Constructs manifests from type checking runs
    - ManifestModel: Pydantic models for validation and schema generation
    - ManifestData: TypedDict definitions for typed manifest structures
    - Versioning: Schema version management and validation
"""

from __future__ import annotations

from .builder import ManifestBuilder
from .loader import load_manifest_data
from .models import (
    EngineErrorModel,
    EngineOptionsModel,
    FileDiagnosticModel,
    FileEntryModel,
    FolderEntryModel,
    ManifestModel,
    ManifestValidationError,
    OverrideEntryModel,
    RunPayloadModel,
    RunSummaryModel,
    ToolSummaryModel,
    manifest_from_model,
    manifest_to_model,
    validate_manifest_payload,
)
from .typed import (
    AggregatedData,
    EngineError,
    EngineOptionsEntry,
    ManifestData,
    RunPayload,
    ToolSummary,
)
from .versioning import (
    CURRENT_MANIFEST_VERSION,
    InvalidManifestRunsError,
    InvalidManifestVersionTypeError,
    ManifestVersion,
    ManifestVersionError,
    UnsupportedManifestVersionError,
    ensure_current_manifest_version,
)

__all__ = [
    "CURRENT_MANIFEST_VERSION",
    "AggregatedData",
    "EngineError",
    "EngineErrorModel",
    "EngineOptionsEntry",
    "EngineOptionsModel",
    "FileDiagnosticModel",
    "FileEntryModel",
    "FolderEntryModel",
    "InvalidManifestRunsError",
    "InvalidManifestVersionTypeError",
    "ManifestBuilder",
    "ManifestData",
    "ManifestModel",
    "ManifestValidationError",
    "ManifestVersion",
    "ManifestVersionError",
    "OverrideEntryModel",
    "RunPayload",
    "RunPayloadModel",
    "RunSummaryModel",
    "ToolSummary",
    "ToolSummaryModel",
    "UnsupportedManifestVersionError",
    "ensure_current_manifest_version",
    "load_manifest_data",
    "manifest_from_model",
    "manifest_to_model",
    "validate_manifest_payload",
]
