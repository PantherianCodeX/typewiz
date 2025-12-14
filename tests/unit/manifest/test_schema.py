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

"""Unit tests for Manifest Schema."""

from __future__ import annotations

import json
from copy import deepcopy
from typing import TYPE_CHECKING, Any, cast

import pytest

from ratchetr._internal.utils import consume
from ratchetr.api import run_audit
from ratchetr.cli import main
from ratchetr.config import AuditConfig
from ratchetr.core.model_types import Mode
from ratchetr.core.type_aliases import EngineName, RunnerName
from ratchetr.manifest.loader import load_manifest_data
from ratchetr.manifest.models import ManifestValidationError, manifest_json_schema, validate_manifest_payload
from ratchetr.manifest.versioning import CURRENT_MANIFEST_VERSION
from ratchetr.services.manifest import emit_manifest_output
from tests.fixtures.stubs import RecordingEngine

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from ratchetr.manifest.typed import ManifestData

pytestmark = pytest.mark.unit


def _patch_engine_resolution(monkeypatch: pytest.MonkeyPatch, engine: RecordingEngine) -> None:
    def _resolve(_: Sequence[str]) -> list[RecordingEngine]:
        return [engine]

    monkeypatch.setattr("ratchetr.engines.resolve_engines", _resolve)
    monkeypatch.setattr("ratchetr.audit.api.resolve_engines", _resolve)


def _sample_manifest() -> ManifestData:
    return {
        "generatedAt": "2025-01-01T00:00:00Z",
        "projectRoot": "/example/project",
        "schemaVersion": CURRENT_MANIFEST_VERSION,
        "runs": [
            {
                "tool": "pyright",
                "mode": Mode.CURRENT,
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
            },
        ],
    }


def test_manifest_validates_against_schema(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    engine = RecordingEngine()
    _patch_engine_resolution(monkeypatch, engine)

    (tmp_path / "src").mkdir(parents=True, exist_ok=True)
    consume((tmp_path / "src" / "mod.py").write_text("x=1\n", encoding="utf-8"))
    manifest_path = tmp_path / "manifest.json"

    override = AuditConfig(full_paths=["src"], runners=[STUB_RUNNER])
    result = run_audit(project_root=tmp_path, override=override)

    emit_manifest_output(result.manifest, manifest_path=manifest_path)

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
    with pytest.raises(ManifestValidationError, match="Input should be a valid string"):
        consume(validate_manifest_payload(manifest))


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
    with pytest.raises(ManifestValidationError, match="Field required"):
        consume(validate_manifest_payload(manifest))


def test_validate_manifest_payload_rejects_extra_fields() -> None:
    manifest = _sample_manifest()
    md = cast("dict[str, Any]", manifest)
    run = cast("dict[str, Any]", md["runs"][0])
    run["unexpectedField"] = "value"
    with pytest.raises(ManifestValidationError, match="Extra inputs are not permitted"):
        consume(validate_manifest_payload(manifest))


def test_validate_manifest_payload_rejects_missing_schema_version() -> None:
    manifest = _sample_manifest()
    manifest_dict = cast("dict[str, Any]", manifest)
    manifest_dict.pop("schemaVersion")
    with pytest.raises(ManifestValidationError, match="Unsupported schemaVersion type") as exc_info:
        consume(validate_manifest_payload(manifest))
    errors = exc_info.value.validation_error.errors()
    assert errors[0]["loc"] == ("schemaVersion",)


def test_validate_manifest_payload_rejects_numeric_schema_version() -> None:
    manifest = _sample_manifest()
    manifest_dict = cast("dict[str, Any]", manifest)
    manifest_dict["schemaVersion"] = 1
    with pytest.raises(ManifestValidationError, match="Unsupported schemaVersion type") as exc_info:
        consume(validate_manifest_payload(manifest))
    errors = exc_info.value.validation_error.errors()
    assert errors[0]["type"].endswith("manifest.version.type")


def test_validate_manifest_payload_rejects_future_schema_version() -> None:
    manifest = _sample_manifest()
    manifest_dict = cast("dict[str, Any]", manifest)
    manifest_dict["schemaVersion"] = "999"
    with pytest.raises(ManifestValidationError, match="Unsupported manifest schema version") as exc_info:
        consume(validate_manifest_payload(manifest))
    errors = exc_info.value.validation_error.errors()
    assert errors[0]["type"].endswith("manifest.version.unsupported")


def test_validate_manifest_payload_rejects_non_list_runs() -> None:
    manifest = _sample_manifest()
    manifest_dict = cast("dict[str, Any]", manifest)
    manifest_dict["runs"] = cast("Any", tuple(manifest_dict["runs"]))
    with pytest.raises(ManifestValidationError, match="runs must be a list of run payloads") as exc_info:
        consume(validate_manifest_payload(manifest))
    errors = exc_info.value.validation_error.errors()
    assert errors[0]["type"].endswith("manifest.runs.type")


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
    assert schema.get("$schema") == "https://json-schema.org/draft-07/schema#"
    assert "$id" in schema
    assert schema.get("additionalProperties") is False


STUB = EngineName("stub")
STUB_RUNNER = RunnerName(STUB)
