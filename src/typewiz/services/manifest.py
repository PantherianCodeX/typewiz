# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Manifest validation and loading services.

This module provides utilities for loading manifest JSON files, validating
their structure against both Pydantic models and JSON Schema, and returning
detailed error information for debugging configuration issues.
"""

from __future__ import annotations

import importlib
import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from typewiz.core.model_types import LogComponent
from typewiz.error_codes import error_code_for
from typewiz.logging import structured_extra
from typewiz.manifest.models import (
    ManifestValidationError,
    manifest_json_schema,
    validate_manifest_payload,
)

if TYPE_CHECKING:
    from pathlib import Path

logger: logging.Logger = logging.getLogger("typewiz.services.manifest")


@dataclass(slots=True)
class ManifestPayloadError:
    """Structured representation of a manifest payload validation error.

    Attributes:
        code: Error code identifying the validation failure type.
        location: Dotted path to the field that failed validation.
        message: Human-readable error description.
    """

    code: str
    location: str
    message: str


@dataclass(slots=True)
class ManifestValidationResult:
    """Complete validation result for a manifest file.

    Attributes:
        payload: Raw dictionary loaded from the manifest JSON.
        payload_errors: List of Pydantic validation errors.
        schema_errors: List of JSON Schema validation errors.
        warnings: Non-fatal warnings (e.g., missing optional dependencies).
    """

    payload: dict[str, object]
    payload_errors: list[ManifestPayloadError]
    schema_errors: list[str]
    warnings: list[str]

    @property
    def is_valid(self) -> bool:
        """Check if the manifest passed all validations.

        Returns:
            True if there are no payload or schema errors.
        """
        return not self.payload_errors and not self.schema_errors


def load_manifest_json(path: Path) -> dict[str, object]:
    """Load and parse a manifest JSON file from disk.

    Args:
        path: Filesystem path to the manifest JSON file.

    Returns:
        Dictionary containing the parsed manifest data.
    """
    payload = cast("dict[str, object]", json.loads(path.read_text(encoding="utf-8")))
    logger.debug(
        "Loaded manifest JSON from %s",
        path,
        extra=structured_extra(component=LogComponent.MANIFEST, path=path),
    )
    return payload


def validate_manifest_file(
    path: Path,
    *,
    schema_path: Path | None = None,
) -> ManifestValidationResult:
    """Validate a manifest file against Pydantic models and optional JSON Schema.

    Args:
        path: Path to the manifest JSON file.
        schema_path: Optional path to a custom JSON Schema file for validation.

    Returns:
        Validation result containing payload, errors, and warnings.
    """
    payload = load_manifest_json(path)
    payload_errors = _validate_payload(payload)
    schema_errors, warnings = _validate_schema(payload, schema_path)
    result = ManifestValidationResult(
        payload=payload,
        payload_errors=payload_errors,
        schema_errors=schema_errors,
        warnings=warnings,
    )
    logger.info(
        "Validated manifest %s (payload_errors=%s schema_errors=%s)",
        path,
        len(payload_errors),
        len(schema_errors),
        extra=structured_extra(
            component=LogComponent.MANIFEST,
            path=path,
            details={
                "payload_errors": len(payload_errors),
                "schema_errors": len(schema_errors),
                "warnings": len(warnings),
            },
        ),
    )
    return result


def _validate_payload(payload: dict[str, object]) -> list[ManifestPayloadError]:
    """Validate manifest payload against Pydantic models.

    Args:
        payload: Raw manifest dictionary to validate.

    Returns:
        List of validation errors, empty if validation succeeds.
    """
    try:
        _ = validate_manifest_payload(payload)
    except ManifestValidationError as exc:
        code = error_code_for(exc)
        errors: list[ManifestPayloadError] = []
        for err in exc.validation_error.errors():
            location = ".".join(str(part) for part in err.get("loc", ())) or "<root>"
            message = err.get("msg", "invalid value")
            errors.append(ManifestPayloadError(code=code, location=location, message=message))
        logger.warning(
            "Manifest payload validation failed (%s errors)",
            len(errors),
            extra=structured_extra(
                component=LogComponent.MANIFEST,
                details={"errors": len(errors), "code": code},
            ),
        )
        return errors
    return []


def _validate_schema(
    payload: dict[str, object],
    schema_path: Path | None,
) -> tuple[list[str], list[str]]:
    """Validate manifest against JSON Schema if available.

    Args:
        payload: Raw manifest dictionary to validate.
        schema_path: Optional custom schema path; uses built-in schema if None.

    Returns:
        Tuple of (schema_errors, warnings).
    """
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
            logger.warning(
                "jsonschema module not available; skipping schema validation",
                extra=structured_extra(component=LogComponent.MANIFEST),
            )
        return [], warnings
    validator = jsonschema_module.Draft7Validator(schema_payload)
    errors = sorted(validator.iter_errors(payload), key=lambda err: err.path)
    schema_errors: list[str] = []
    for err in errors:
        loc = "/".join(str(part) for part in err.path)
        schema_errors.append(f"[typewiz] schema error at /{loc}: {err.message}")
    if schema_errors:
        logger.warning(
            "Manifest schema validation failed (%s errors)",
            len(schema_errors),
            extra=structured_extra(
                component=LogComponent.MANIFEST,
                details={"errors": len(schema_errors)},
            ),
        )
    return schema_errors, warnings


__all__ = [
    "ManifestPayloadError",
    "ManifestValidationResult",
    "load_manifest_json",
    "manifest_json_schema",
    "validate_manifest_file",
]
