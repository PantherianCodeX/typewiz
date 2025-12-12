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

"""Public shim for runtime path resolution helpers."""

from __future__ import annotations

from ratchetr._internal.paths import (
    CACHE_ENV,
    CONFIG_ENV,
    DEFAULT_CACHE_DIRNAME,
    DEFAULT_DASHBOARD_FILENAME,
    DEFAULT_LOG_DIRNAME,
    DEFAULT_MANIFEST_FILENAME,
    DEFAULT_TOOL_HOME_DIRNAME,
    LOG_ENV,
    MANIFEST_CANDIDATE_NAMES,
    MANIFEST_ENV,
    ROOT_ENV,
    TOOL_HOME_ENV,
    EnvOverrides,
    ManifestDiagnostics,
    ManifestDiscoveryError,
    ManifestDiscoveryResult,
    OutputFormat,
    OutputPlan,
    OutputTarget,
    PathOverrides,
    ResolvedPaths,
    discover_manifest,
    resolve_paths,
)

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
