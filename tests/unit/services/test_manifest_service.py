# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Unit tests for manifest validation helpers."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from typewiz.services import manifest as manifest_service

if TYPE_CHECKING:
    from pathlib import Path
    from types import ModuleType

    import pytest


def _write_manifest(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _basic_manifest() -> dict[str, object]:
    return {
        "projectRoot": ".",
        "generatedAt": "now",
        "schemaVersion": 1,
        "runs": [],
    }


def _custom_schema(path: Path) -> None:
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {"foo": {"type": "string"}},
        "required": ["foo"],
    }
    path.write_text(json.dumps(schema), encoding="utf-8")


def test_manifest_validation_reports_payload_errors(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    _write_manifest(manifest_path, {"schemaVersion": 1, "runs": "invalid"})
    result = manifest_service.validate_manifest_file(manifest_path)
    assert not result.is_valid
    assert result.payload_errors
    assert result.schema_errors


def test_manifest_validation_detects_schema_errors(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    schema_path = tmp_path / "schema.json"
    _write_manifest(manifest_path, _basic_manifest())
    _custom_schema(schema_path)
    result = manifest_service.validate_manifest_file(manifest_path, schema_path=schema_path)
    assert result.schema_errors
    assert result.payload_errors


def test_manifest_validation_warns_when_jsonschema_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest_path = tmp_path / "manifest.json"
    _write_manifest(manifest_path, _basic_manifest())
    schema_path = tmp_path / "schema.json"
    _custom_schema(schema_path)
    original_import = manifest_service.importlib.import_module

    def fake_import(name: str) -> ModuleType:
        if name == "jsonschema":
            raise ModuleNotFoundError
        return original_import(name)

    monkeypatch.setattr(manifest_service.importlib, "import_module", fake_import)
    result = manifest_service.validate_manifest_file(manifest_path, schema_path=schema_path)
    assert "[typewiz] jsonschema module not available" in result.warnings[0]
    assert result.schema_errors == []


def test_validate_schema_skips_when_schema_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = _basic_manifest()
    monkeypatch.setattr(manifest_service, "manifest_json_schema", lambda: None)
    schema_errors, warnings = manifest_service._validate_schema(manifest, schema_path=None)
    assert schema_errors == []
    assert warnings == []


def test_validate_schema_warns_when_jsonschema_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    payload = _basic_manifest()
    schema_path = tmp_path / "schema.json"
    _custom_schema(schema_path)

    original_import = manifest_service.importlib.import_module

    def fake_import(name: str) -> ModuleType:
        if name == "jsonschema":
            raise ModuleNotFoundError
        return original_import(name)

    monkeypatch.setattr(manifest_service.importlib, "import_module", fake_import)
    schema_errors, warnings = manifest_service._validate_schema(payload, schema_path)
    assert schema_errors == []
    assert warnings
