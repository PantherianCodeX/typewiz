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

"""Unit tests for Ratchet IO."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest
from pydantic import ValidationError

from ratchetr.config.constants import DEFAULT_RATCHET_FILENAME
from ratchetr.manifest.versioning import CURRENT_MANIFEST_VERSION
from ratchetr.ratchet.io import current_timestamp, load_manifest, load_ratchet, write_ratchet
from ratchetr.ratchet.models import RatchetModel

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = [pytest.mark.unit, pytest.mark.ratchet]


def _sample_model(tmp_path: Path) -> RatchetModel:
    return RatchetModel.model_validate({
        "generatedAt": "2025-01-01T00:00:00Z",
        "manifestPath": str(tmp_path / ".ratchetr/manifest"),
        "projectRoot": str(tmp_path),
        "runs": {
            "pyright:current": {
                "severities": ["error"],
                "paths": {},
                "targets": {"error": 1},
            }
        },
    })


def test_write_and_load_ratchet_round_trip(tmp_path: Path) -> None:
    model = _sample_model(tmp_path)
    ratchet_path = tmp_path / DEFAULT_RATCHET_FILENAME
    write_ratchet(ratchet_path, model)

    loaded = load_ratchet(ratchet_path)
    assert loaded.model_dump() == model.model_dump()


def test_load_ratchet_invalid_payload(tmp_path: Path) -> None:
    ratchet_path = tmp_path / DEFAULT_RATCHET_FILENAME
    _ = ratchet_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValidationError, match="Field required"):
        _ = load_ratchet(ratchet_path)


def test_current_timestamp_includes_timezone() -> None:
    stamp = current_timestamp()
    assert stamp.endswith("+00:00")


def test_load_manifest_round_trip(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_payload: dict[str, object] = {
        "schemaVersion": CURRENT_MANIFEST_VERSION,
        "projectRoot": str(tmp_path),
        "generatedAt": "now",
        "runs": [],
    }
    _ = manifest_path.write_text(json.dumps(manifest_payload), encoding="utf-8")

    manifest = load_manifest(manifest_path)
    assert manifest.get("schemaVersion") == CURRENT_MANIFEST_VERSION
