# Copyright (c) 2024 PantherianCodeX
"""Manifest command implementation for the modular Typewiz CLI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Protocol

from typewiz.core.model_types import ManifestAction
from typewiz.services.manifest import (
    manifest_json_schema,
    validate_manifest_file,
)

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


def _handle_validate(args: argparse.Namespace) -> int:
    result = validate_manifest_file(args.path, schema_path=args.schema)
    for err in result.payload_errors:
        echo(f"[typewiz] ({err.code}) validation error at {err.location}: {err.message}")
    for message in result.schema_errors:
        echo(message)
    for warning in result.warnings:
        echo(warning)
    if result.is_valid:
        echo("[typewiz] manifest is valid")
        return 0
    return 2


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
