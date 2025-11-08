# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final, Literal

type ManifestVersion = Literal["1"]

CURRENT_MANIFEST_VERSION: Final[ManifestVersion] = "1"


class ManifestVersionError(ValueError):
    """Base error for manifest version issues."""


class InvalidManifestVersionTypeError(ManifestVersionError):
    """Raised when ``schemaVersion`` is not a string or numeric literal."""

    def __init__(self, value: object) -> None:
        self.value = value
        super().__init__(f"Unsupported schemaVersion type: {type(value)!r}")


class UnsupportedManifestVersionError(ManifestVersionError):
    """Raised when a manifest declares a future or unknown schema version."""

    def __init__(self, version: str) -> None:
        self.version = version
        super().__init__(f"Unsupported manifest schema version: {version}")


class InvalidManifestRunsError(ManifestVersionError):
    """Raised when the manifest ``runs`` block is not a list."""

    def __init__(self) -> None:
        super().__init__("runs must be a list of run payloads")


def _normalize_version(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    raise InvalidManifestVersionTypeError(value)


def ensure_current_manifest_version(manifest: Mapping[str, Any]) -> ManifestVersion:
    """Validate that a manifest declares the currently supported schema version."""

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
    "ensure_current_manifest_version",
    "InvalidManifestRunsError",
    "InvalidManifestVersionTypeError",
    "ManifestVersionError",
    "UnsupportedManifestVersionError",
]
