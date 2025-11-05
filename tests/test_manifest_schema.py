from __future__ import annotations

import json
from collections.abc import Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any, cast

import pytest

from typewiz.api import run_audit
from typewiz.cli import main
from typewiz.config import AuditConfig
from typewiz.engines.base import EngineContext, EngineResult
from typewiz.manifest_loader import load_manifest_data
from typewiz.manifest_models import (
    ManifestValidationError,
    manifest_json_schema,
    validate_manifest_payload,
)
from typewiz.manifest_versioning import CURRENT_MANIFEST_VERSION
from typewiz.model_types import CategoryMapping
from typewiz.typed_manifest import ManifestData


class RecordingEngine:
    name = "stub"

    def run(self, context: EngineContext, paths: Sequence[str]) -> EngineResult:
        return EngineResult(
            engine=self.name,
            mode=context.mode,
            command=["stub", context.mode],
            exit_code=0,
            duration_ms=0.1,
            diagnostics=[],
        )

    def category_mapping(self) -> CategoryMapping:
        return {}

    def fingerprint_targets(self, context: EngineContext, paths: Sequence[str]) -> Sequence[str]:
        return []


def _patch_engine_resolution(monkeypatch: pytest.MonkeyPatch, engine: RecordingEngine) -> None:
    def _resolve(_: Sequence[str]) -> list[RecordingEngine]:
        return [engine]

    monkeypatch.setattr("typewiz.engines.resolve_engines", _resolve)
    monkeypatch.setattr("typewiz.api.resolve_engines", _resolve)


def _sample_manifest() -> ManifestData:
    return {
        "generatedAt": "2025-01-01T00:00:00Z",
        "projectRoot": "/example/project",
        "schemaVersion": "1",
        "runs": [
            {
                "tool": "pyright",
                "mode": "current",
                "command": ["pyright", "--project"],
                "exitCode": 0,
                "durationMs": 0.25,
                "summary": {
                    "errors": 0,
                    "warnings": 0,
                    "information": 0,
                    "total": 0,
                },
                "perFile": [],
                "perFolder": [],
                "engineOptions": {
                    "pluginArgs": [],
                    "include": [],
                    "exclude": [],
                    "overrides": [],
                },
                "toolSummary": {
                    "errors": 0,
                    "warnings": 0,
                    "information": 0,
                    "total": 0,
                },
            }
        ],
    }


def test_manifest_validates_against_schema(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    engine = RecordingEngine()
    _patch_engine_resolution(monkeypatch, engine)

    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    (tmp_path / "src" / "mod.py").write_text("x=1\n", encoding="utf-8")
    manifest_path = tmp_path / "manifest.json"

    override = AuditConfig(full_paths=["src"], runners=["stub"])
    run_audit(project_root=tmp_path, override=override, write_manifest_to=manifest_path)

    # Use the CLI validator to exercise both the jsonschema and fallback paths
    code = main(["manifest", "validate", str(manifest_path)])
    assert code == 0


def test_validate_manifest_payload_round_trip() -> None:
    manifest = _sample_manifest()
    validated = validate_manifest_payload(deepcopy(manifest))
    assert "runs" in validated
    assert validated["runs"][0]["tool"] == "pyright"
    loaded = load_manifest_data(deepcopy(manifest))
    assert "runs" in loaded
    assert loaded["runs"][0]["command"] == ["pyright", "--project"]


def test_validate_manifest_payload_rejects_invalid_tool() -> None:
    manifest = _sample_manifest()
    m = cast("dict[str, Any]", manifest)
    invalid_run = cast("dict[str, Any]", m["runs"][0])
    invalid_run["tool"] = 123
    with pytest.raises(ManifestValidationError):
        validate_manifest_payload(manifest)
    coerced = load_manifest_data(manifest)
    assert "runs" in coerced
    assert coerced["runs"] == []


def test_validate_manifest_payload_accepts_missing_optionals() -> None:
    # Drop optional fields and ensure validation still passes
    manifest = _sample_manifest()
    md = cast("dict[str, Any]", manifest)
    run = cast("dict[str, Any]", md["runs"][0])
    run.pop("toolSummary")
    run.pop("engineArgsEffective", None)
    run.pop("scannedPathsResolved", None)
    validated = validate_manifest_payload(manifest)
    vd = cast("dict[str, Any]", validated)
    assert "toolSummary" not in vd["runs"][0]


def test_validate_manifest_payload_rejects_malformed_perfile() -> None:
    manifest = _sample_manifest()
    md = cast("dict[str, Any]", manifest)
    run = cast("dict[str, Any]", md["runs"][0])
    run["perFile"] = [{}]
    with pytest.raises(ManifestValidationError):
        validate_manifest_payload(manifest)


def test_validate_manifest_payload_rejects_extra_fields() -> None:
    manifest = _sample_manifest()
    md = cast("dict[str, Any]", manifest)
    run = cast("dict[str, Any]", md["runs"][0])
    run["unexpectedField"] = "value"
    with pytest.raises(ManifestValidationError):
        validate_manifest_payload(manifest)


def test_validate_manifest_payload_upgrades_missing_schema_version() -> None:
    manifest = _sample_manifest()
    manifest_dict = cast("dict[str, Any]", manifest)
    manifest_dict.pop("schemaVersion")
    validated = validate_manifest_payload(manifest)
    assert validated.get("schemaVersion") == CURRENT_MANIFEST_VERSION


def test_validate_manifest_payload_accepts_numeric_schema_version() -> None:
    manifest = _sample_manifest()
    manifest_dict = cast("dict[str, Any]", manifest)
    manifest_dict["schemaVersion"] = 1
    validated = validate_manifest_payload(manifest)
    assert validated.get("schemaVersion") == CURRENT_MANIFEST_VERSION


def test_manifest_schema_cli_round_trip(tmp_path: Path) -> None:
    manifest = _sample_manifest()
    schema_path = tmp_path / "manifest.schema.json"

    exit_code = main(["manifest", "schema", "--output", str(schema_path)])
    assert exit_code == 0

    schema_text = schema_path.read_text(encoding="utf-8")
    schema = json.loads(schema_text)
    assert schema == manifest_json_schema()

    jsonschema = pytest.importorskip("jsonschema")
    validator = jsonschema.Draft7Validator(schema)
    validator.validate(manifest)

    validated = validate_manifest_payload(manifest)
    assert "runs" in validated
    assert validated["runs"][0]["durationMs"] == 0.25


def test_manifest_schema_includes_metadata() -> None:
    schema = manifest_json_schema()
    assert schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema"
    assert "$id" in schema
    assert schema.get("additionalProperties") is False


def test_manifest_migrate_cli(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(_sample_manifest()), encoding="utf-8")
    output_path = tmp_path / "migrated.json"

    exit_code = main(
        [
            "manifest",
            "migrate",
            "--input",
            str(manifest_path),
            "--output",
            str(output_path),
        ]
    )
    assert exit_code == 0
    migrated = json.loads(output_path.read_text(encoding="utf-8"))
    assert "runs" in migrated


def test_manifest_migrate_cli_rejects_non_object(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text("[]", encoding="utf-8")

    exit_code = main(
        [
            "manifest",
            "migrate",
            "--input",
            str(manifest_path),
        ]
    )
    assert exit_code == 2
    captured = capsys.readouterr()
    assert "expects a JSON object payload" in captured.out
