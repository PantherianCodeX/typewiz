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

"""I/O helpers for ratchet artefacts and manifests."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from ratchetr.compat import UTC
from ratchetr.json import normalise_enums_for_json
from ratchetr.manifest.loader import load_manifest_data

from .models import RatchetModel

if TYPE_CHECKING:
    from pathlib import Path

    from ratchetr.manifest.typed import ManifestData


def current_timestamp() -> str:
    """Return an ISO timestamp in UTC.

    Returns:
        Timestamp string suitable for manifest metadata.
    """
    return datetime.now(UTC).isoformat()


def load_ratchet(path: Path) -> RatchetModel:
    """Load and validate a ratchet file from disk.

    Args:
        path: Location of the ratchet JSON file.

    Returns:
        Validated `RatchetModel`instance.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    return RatchetModel.model_validate(payload)


def write_ratchet(path: Path, model: RatchetModel) -> None:
    """Persist a ratchet model to disk."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = model.model_dump(by_alias=True, exclude_none=True)
    payload_json = normalise_enums_for_json(payload)
    _ = path.write_text(json.dumps(payload_json, indent=2) + "\n", encoding="utf-8")


def load_manifest(path: Path) -> ManifestData:
    """Load and validate a manifest file.

    Args:
        path: Location of the manifest JSON file.

    Returns:
        `ManifestData`mapping ready for downstream processing.
    """
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
