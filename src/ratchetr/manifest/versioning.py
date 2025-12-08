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

"""Manifest schema versioning and validation.

This module manages manifest schema versions and provides validation to ensure
manifests conform to supported versions. It defines version-specific errors
and validation functions to handle version compatibility.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final, Literal, TypeAlias

if TYPE_CHECKING:
    from collections.abc import Mapping

ManifestVersion: TypeAlias = Literal["1"]

CURRENT_MANIFEST_VERSION: Final[ManifestVersion] = "1"


class ManifestVersionError(ValueError):
    """Base error for manifest version-related issues."""


class InvalidManifestVersionTypeError(ManifestVersionError):
    """Raised when schemaVersion is not a string or numeric literal.

    Attributes:
        value: The invalid value that was provided.
    """

    def __init__(self, value: object) -> None:
        """Initialize with the invalid version value.

        Args:
            value: The invalid schemaVersion value.
        """
        self.value = value
        super().__init__(f"Unsupported schemaVersion type: {type(value)!r}")


class UnsupportedManifestVersionError(ManifestVersionError):
    """Raised when a manifest declares a future or unknown schema version.

    Attributes:
        version: The unsupported version string.
    """

    def __init__(self, version: str) -> None:
        """Initialize with the unsupported version.

        Args:
            version: The unsupported schema version string.
        """
        self.version = version
        super().__init__(f"Unsupported manifest schema version: {version}")


class InvalidManifestRunsError(ManifestVersionError):
    """Raised when the manifest runs block is not a list."""

    def __init__(self) -> None:
        """Initialize the error with a standard message."""
        super().__init__("runs must be a list of run payloads")


def _normalize_version(value: object) -> str:
    """Normalize and validate a schema version value.

    Args:
        value: The raw schemaVersion value from a manifest.

    Returns:
        Normalized version string (stripped of whitespace).

    Raises:
        InvalidManifestVersionTypeError: If value is not a string.
    """
    if isinstance(value, str):
        return value.strip()
    raise InvalidManifestVersionTypeError(value)


def ensure_current_manifest_version(manifest: Mapping[str, Any]) -> ManifestVersion:
    """Validate that a manifest declares the currently supported schema version.

    Checks both the schema version and that the runs field (if present) is a list.

    Args:
        manifest: Raw manifest data as a mapping.

    Returns:
        The current manifest version if validation succeeds.

    Raises:
        UnsupportedManifestVersionError: If schemaVersion is not supported.
        InvalidManifestRunsError: If runs field is present but not a list.
    """
    version_raw = manifest.get("schemaVersion")
    version = _normalize_version(version_raw)
    if version != CURRENT_MANIFEST_VERSION:
        raise UnsupportedManifestVersionError(version)
    runs_raw = manifest.get("runs")
    if runs_raw is not None and not isinstance(runs_raw, list):
        raise InvalidManifestRunsError
    return CURRENT_MANIFEST_VERSION


__all__ = [
    "CURRENT_MANIFEST_VERSION",
    "InvalidManifestRunsError",
    "InvalidManifestVersionTypeError",
    "ManifestVersionError",
    "UnsupportedManifestVersionError",
    "ensure_current_manifest_version",
]
