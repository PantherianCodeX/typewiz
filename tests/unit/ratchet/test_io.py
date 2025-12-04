# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Unit tests for Ratchet IO."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from typewiz.manifest.versioning import CURRENT_MANIFEST_VERSION
from typewiz.ratchet.io import current_timestamp, load_manifest, load_ratchet, write_ratchet
from typewiz.ratchet.models import RatchetModel

pytestmark = [pytest.mark.unit, pytest.mark.ratchet]


def _sample_model(tmp_path: Path) -> RatchetModel:
    return RatchetModel.model_validate({
        "generatedAt": "2025-01-01T00:00:00Z",
        "manifestPath": str(tmp_path / "typing_audit.json"),
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
    ratchet_path = tmp_path / "ratchet.json"
    write_ratchet(ratchet_path, model)

    loaded = load_ratchet(ratchet_path)
    assert loaded.model_dump() == model.model_dump()


def test_load_ratchet_invalid_payload(tmp_path: Path) -> None:
    ratchet_path = tmp_path / "ratchet.json"
    _ = ratchet_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValidationError):
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
