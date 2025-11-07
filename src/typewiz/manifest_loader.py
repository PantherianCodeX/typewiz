# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from typing import Any, TypeGuard, cast

from .data_validation import coerce_mapping
from .manifest_models import ManifestValidationError, validate_manifest_payload
from .model_types import Mode
from .typed_manifest import ManifestData, RunPayload

logger: logging.Logger = logging.getLogger("typewiz.manifest_loader")


def _is_run_payload(obj: object) -> TypeGuard[RunPayload]:
    if not isinstance(obj, Mapping):
        return False
    typed_obj = cast(Mapping[str, object], obj)
    required_keys = {"tool", "mode", "summary", "perFile", "perFolder", "engineOptions"}
    if not required_keys.issubset({str(key) for key in typed_obj}):
        return False
    tool_value = typed_obj.get("tool")
    mode_value = typed_obj.get("mode")
    if not isinstance(tool_value, str) or not isinstance(mode_value, (str, Mode)):
        return False
    if not isinstance(typed_obj.get("command"), list):
        return False
    if not isinstance(typed_obj.get("summary"), Mapping):
        return False
    if not isinstance(typed_obj.get("perFile"), list) or not isinstance(
        typed_obj.get("perFolder"),
        list,
    ):
        return False
    return isinstance(typed_obj.get("engineOptions"), Mapping)


def _coerce_manifest_mapping(raw: Mapping[str, object]) -> ManifestData:
    manifest_obj = coerce_mapping(raw)
    manifest: ManifestData = {}

    generated_at = manifest_obj.get("generatedAt")
    if isinstance(generated_at, str):
        manifest["generatedAt"] = generated_at

    project_root = manifest_obj.get("projectRoot")
    if isinstance(project_root, str):
        manifest["projectRoot"] = project_root

    schema_version = manifest_obj.get("schemaVersion")
    if isinstance(schema_version, str):
        manifest["schemaVersion"] = schema_version

    fingerprint_truncated = manifest_obj.get("fingerprintTruncated")
    if isinstance(fingerprint_truncated, bool):
        manifest["fingerprintTruncated"] = fingerprint_truncated

    tool_versions = manifest_obj.get("toolVersions")
    if isinstance(tool_versions, Mapping):
        manifest["toolVersions"] = {
            str(key): str(value) for key, value in tool_versions.items() if isinstance(value, str)
        }

    runs_field = manifest_obj.get("runs")
    runs_list: list[RunPayload] = []
    if isinstance(runs_field, Sequence):
        for item in runs_field:
            if _is_run_payload(item):
                runs_list.append(item)
            else:
                logger.debug("Skipping invalid run entry during manifest load: %s", item)
    manifest["runs"] = runs_list
    return manifest


def load_manifest_data(raw: Any) -> ManifestData:
    """Parse manifest-like payloads using strict validation with a tolerant fallback."""

    try:
        return validate_manifest_payload(raw)
    except ManifestValidationError as exc:
        logger.debug(
            "Manifest validation failed; falling back to coercion: %s",
            exc.validation_error,
        )
        if not isinstance(raw, Mapping):
            raise
        return _coerce_manifest_mapping(cast(Mapping[str, object], raw))
