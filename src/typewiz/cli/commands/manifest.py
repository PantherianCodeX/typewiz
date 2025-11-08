# Copyright (c) 2024 PantherianCodeX
"""Manifest command implementation for the modular Typewiz CLI."""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
from typing import Any, Protocol, cast

from typewiz._internal.error_codes import error_code_for
from typewiz.manifest_models import (
    ManifestValidationError,
    manifest_json_schema,
    validate_manifest_payload,
)
from typewiz.model_types import ManifestAction
from typewiz.utils import consume

from ..helpers import echo, register_argument


class SubparserRegistry(Protocol):
    def add_parser(
        self, *args: Any, **kwargs: Any
    ) -> argparse.ArgumentParser: ...  # pragma: no cover - Protocol


def register_manifest_command(subparsers: SubparserRegistry) -> None:
    """Register the ``typewiz manifest`` command."""
    manifest_cmd = subparsers.add_parser(
        "manifest",
        help="Work with manifest files (validate)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    manifest_sub = manifest_cmd.add_subparsers(dest="action", required=True)

    manifest_validate = manifest_sub.add_parser(
        ManifestAction.VALIDATE.value,
        help="Validate a manifest against the JSON schema",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    register_argument(
        manifest_validate,
        "path",
        type=Path,
        help="Path to manifest file to validate",
    )
    register_argument(
        manifest_validate,
        "--schema",
        type=Path,
        default=None,
        help="Optionally validate against an additional JSON schema",
    )

    manifest_schema = manifest_sub.add_parser(
        ManifestAction.SCHEMA.value,
        help="Emit the manifest JSON schema",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    register_argument(
        manifest_schema,
        "--output",
        type=Path,
        default=None,
        help="Write the schema to a path instead of stdout",
    )
    register_argument(
        manifest_schema,
        "--indent",
        type=int,
        default=2,
        help="Indentation level for JSON output",
    )


def _validate_schema(schema_path: Path | None, payload: dict[str, object]) -> bool:
    schema_payload: dict[str, Any] | None
    if schema_path is not None:
        schema_payload = json.loads(schema_path.read_text(encoding="utf-8"))
    else:
        schema_payload = manifest_json_schema()

    if schema_payload is None:
        return True
    try:
        jsonschema_module = importlib.import_module("jsonschema")
    except ModuleNotFoundError:
        if schema_path is not None:
            echo("[typewiz] jsonschema module not available; skipping schema validation")
        return True

    validator = jsonschema_module.Draft7Validator(schema_payload)
    errors = sorted(validator.iter_errors(payload), key=lambda err: err.path)
    if not errors:
        return True
    for err in errors:
        loc = "/".join(str(part) for part in err.path)
        echo(f"[typewiz] schema error at /{loc}: {err.message}")
    return False


def _handle_validate(args: argparse.Namespace) -> int:
    manifest_path: Path = args.path
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    try:
        consume(validate_manifest_payload(payload))
    except ManifestValidationError as exc:
        code = error_code_for(exc)
        for err in exc.validation_error.errors():
            location = ".".join(str(part) for part in err.get("loc", ())) or "<root>"
            message = err.get("msg", "invalid value")
            echo(f"[typewiz] ({code}) validation error at {location}: {message}")
        return 2

    if not _validate_schema(args.schema, cast("dict[str, object]", payload)):
        return 2

    echo("[typewiz] manifest is valid")
    return 0


def _handle_schema(args: argparse.Namespace) -> int:
    schema = manifest_json_schema()
    schema_text = json.dumps(schema, indent=args.indent)
    if args.output:
        _ = args.output.parent.mkdir(parents=True, exist_ok=True)
        _ = args.output.write_text(schema_text + "\n", encoding="utf-8")
    else:
        echo(schema_text)
    return 0


def execute_manifest(args: argparse.Namespace) -> int:
    """Execute the ``typewiz manifest`` command."""
    action_value = args.action
    try:
        action = (
            action_value
            if isinstance(action_value, ManifestAction)
            else ManifestAction.from_str(action_value)
        )
    except ValueError as exc:  # pragma: no cover - argparse prevents invalid choices
        raise SystemExit(str(exc)) from exc
    if action is ManifestAction.VALIDATE:
        return _handle_validate(args)
    if action is ManifestAction.SCHEMA:
        return _handle_schema(args)
    raise SystemExit("Unknown manifest action")


__all__ = ["execute_manifest", "register_manifest_command"]
