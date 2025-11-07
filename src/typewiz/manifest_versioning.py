# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final, Literal, cast

type ManifestVersion = Literal["1"]
type LegacyManifestVersion = Literal["0", ""]

CURRENT_MANIFEST_VERSION: Final[ManifestVersion] = "1"
LEGACY_MANIFEST_VERSIONS: Final[tuple[LegacyManifestVersion, ...]] = ("0", "")


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


def _normalize_version(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    raise InvalidManifestVersionTypeError(value)


def _ensure_runs(value: object) -> list[object]:
    if value is None:
        return []
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return list(cast(Sequence[object], value))
    raise InvalidManifestRunsError


def upgrade_manifest(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Upgrade a manifest payload to the current schema version."""

    working = dict(manifest)
    version_raw = _normalize_version(working.get("schemaVersion"))

    if version_raw in LEGACY_MANIFEST_VERSIONS or version_raw is None:
        upgraded = dict(working)
        upgraded["schemaVersion"] = CURRENT_MANIFEST_VERSION
        upgraded["runs"] = _ensure_runs(upgraded.get("runs"))
        return upgraded

    if version_raw != CURRENT_MANIFEST_VERSION:
        raise UnsupportedManifestVersionError(version_raw)

    working["schemaVersion"] = CURRENT_MANIFEST_VERSION
    working["runs"] = _ensure_runs(working.get("runs"))
    return working


__all__ = [
    "CURRENT_MANIFEST_VERSION",
    "InvalidManifestRunsError",
    "InvalidManifestVersionTypeError",
    "ManifestVersionError",
    "UnsupportedManifestVersionError",
    "upgrade_manifest",
]
