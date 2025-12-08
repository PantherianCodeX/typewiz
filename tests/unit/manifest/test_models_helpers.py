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

"""Supplemental tests for manifest models helpers."""

from __future__ import annotations

from ratchetr.manifest.models import (
    _empty_override_list,
    _empty_run_payload_list,
    manifest_from_model,
    manifest_json_schema,
    manifest_to_model,
)


def test_empty_override_and_run_lists_are_empty() -> None:
    assert _empty_override_list() == []
    assert _empty_run_payload_list() == []


def test_manifest_model_round_trip() -> None:
    manifest = {
        "generatedAt": "now",
        "projectRoot": ".",
        "schemaVersion": "1",
        "runs": [],
    }
    model = manifest_to_model(manifest)
    data = manifest_from_model(model)
    assert data["generatedAt"] == manifest["generatedAt"]
    assert data["schemaVersion"] == manifest["schemaVersion"]


def test_manifest_json_schema_contains_metadata() -> None:
    schema = manifest_json_schema()
    assert "$schema" in schema
    assert schema["additionalProperties"] is False
