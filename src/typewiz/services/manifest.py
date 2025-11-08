from __future__ import annotations

import importlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from typewiz.error_codes import error_code_for
from typewiz.manifest.models import (
    ManifestValidationError,
    manifest_json_schema,
    validate_manifest_payload,
)


@dataclass(slots=True)
class ManifestPayloadError:
    code: str
    location: str
    message: str


@dataclass(slots=True)
class ManifestValidationResult:
    payload: dict[str, object]
    payload_errors: list[ManifestPayloadError]
    schema_errors: list[str]
    warnings: list[str]

    @property
    def is_valid(self) -> bool:
        return not self.payload_errors and not self.schema_errors


def load_manifest_json(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def validate_manifest_file(
    path: Path,
    *,
    schema_path: Path | None = None,
) -> ManifestValidationResult:
    payload = load_manifest_json(path)
    payload_errors = _validate_payload(payload)
    schema_errors, warnings = _validate_schema(payload, schema_path)
    return ManifestValidationResult(
        payload=payload,
        payload_errors=payload_errors,
        schema_errors=schema_errors,
        warnings=warnings,
    )


def _validate_payload(payload: dict[str, object]) -> list[ManifestPayloadError]:
    try:
        _ = validate_manifest_payload(payload)
    except ManifestValidationError as exc:
        code = error_code_for(exc)
        errors: list[ManifestPayloadError] = []
        for err in exc.validation_error.errors():
            location = ".".join(str(part) for part in err.get("loc", ())) or "<root>"
            message = err.get("msg", "invalid value")
            errors.append(ManifestPayloadError(code=code, location=location, message=message))
        return errors
    return []


def _validate_schema(
    payload: dict[str, object],
    schema_path: Path | None,
) -> tuple[list[str], list[str]]:
    schema_payload: dict[str, Any] | None
    if schema_path is not None:
        schema_payload = json.loads(schema_path.read_text(encoding="utf-8"))
    else:
        schema_payload = manifest_json_schema()
    if schema_payload is None:
        return [], []
    warnings: list[str] = []
    try:
        jsonschema_module = importlib.import_module("jsonschema")
    except ModuleNotFoundError:
        if schema_path is not None:
            warnings.append(
                "[typewiz] jsonschema module not available; skipping schema validation",
            )
        return [], warnings
    validator = jsonschema_module.Draft7Validator(schema_payload)
    errors = sorted(validator.iter_errors(payload), key=lambda err: err.path)
    schema_errors: list[str] = []
    for err in errors:
        loc = "/".join(str(part) for part in err.path)
        schema_errors.append(f"[typewiz] schema error at /{loc}: {err.message}")
    return schema_errors, warnings


__all__ = [
    "ManifestPayloadError",
    "ManifestValidationResult",
    "load_manifest_json",
    "manifest_json_schema",
    "validate_manifest_file",
]
