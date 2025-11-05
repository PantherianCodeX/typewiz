from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Final, cast

CURRENT_MANIFEST_VERSION: Final[str] = "1"
LEGACY_MANIFEST_VERSIONS: Final[tuple[str, ...]] = ("0", "")


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


def _normalize_version(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    raise InvalidManifestVersionTypeError(value)


def _ensure_runs(value: object) -> list[object]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return list(cast(Sequence[object], value))
    return []


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
    "InvalidManifestVersionTypeError",
    "ManifestVersionError",
    "UnsupportedManifestVersionError",
    "upgrade_manifest",
]
