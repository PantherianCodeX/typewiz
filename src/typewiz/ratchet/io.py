# Copyright (c) 2024 PantherianCodeX
"""I/O helpers for ratchet artefacts and manifests."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from ..manifest_loader import load_manifest_data
from ..utils import normalise_enums_for_json
from .models import RatchetModel

if TYPE_CHECKING:
    from ..typed_manifest import ManifestData


def current_timestamp() -> str:
    """Return an ISO timestamp in UTC."""

    return datetime.now(UTC).isoformat()


def load_ratchet(path: Path) -> RatchetModel:
    """Load and validate a ratchet file from disk."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    return RatchetModel.model_validate(payload)


def write_ratchet(path: Path, model: RatchetModel) -> None:
    """Persist a ratchet model to disk."""

    path.parent.mkdir(parents=True, exist_ok=True)
    payload = model.model_dump(by_alias=True, exclude_none=True)
    payload_json = normalise_enums_for_json(payload)
    _ = path.write_text(json.dumps(payload_json, indent=2) + "\n", encoding="utf-8")


def load_manifest(path: Path) -> ManifestData:
    """Load and validate a manifest file."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    return load_manifest_data(payload)


def write_text(path: Path, content: str) -> None:
    """Write text to path ensuring parents exist."""

    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(content, encoding="utf-8")


__all__ = [
    "current_timestamp",
    "load_manifest",
    "load_ratchet",
    "write_ratchet",
    "write_text",
]
