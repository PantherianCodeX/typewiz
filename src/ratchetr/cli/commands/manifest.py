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

"""Manifest command implementation for the modular ratchetr CLI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

from ratchetr.cli.helpers import discover_manifest_or_exit, echo, register_argument
from ratchetr.core.model_types import ManifestAction
from ratchetr.services.manifest import (
    manifest_json_schema,
    validate_manifest_file,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ratchetr.cli.helpers import CLIContext
    from ratchetr.cli.types import SubparserCollection
    from ratchetr.compat import Never


def _raise_unknown_manifest_action(action: Never) -> NoReturn:
    msg = f"Unknown manifest action: {action}"
    raise SystemExit(msg)


def register_manifest_command(
    subparsers: SubparserCollection,
    *,
    parents: Sequence[argparse.ArgumentParser] | None = None,
) -> None:
    """Register the `ratchetr manifest` command.

    Args:
        subparsers: Top-level argparse subparser collection to register commands on.
        parents: Shared parent parsers carrying global options.
    """
    manifest_cmd = subparsers.add_parser(
        "manifest",
        help="Work with manifest files (validate)",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        parents=parents or [],
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
        nargs="?",
        type=Path,
        default=None,
        help="Path to manifest file to validate (default: discovered manifest)",
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


def _handle_validate(args: argparse.Namespace, context: CLIContext) -> int:
    manifest_path = args.path or discover_manifest_or_exit(context, cli_manifest=getattr(args, "manifest", None))
    result = validate_manifest_file(manifest_path, schema_path=args.schema)
    for err in result.payload_errors:
        echo(f"[ratchetr] ({err.code}) validation error at {err.location}: {err.message}")
    for message in result.schema_errors:
        echo(message)
    for warning in result.warnings:
        echo(warning)
    if result.is_valid:
        echo("[ratchetr] manifest is valid")
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


def execute_manifest(args: argparse.Namespace, context: CLIContext) -> int:
    """Execute the `ratchetr manifest` command.

    Args:
        args: Parsed CLI namespace describing the requested action.
        context: Shared CLI context containing resolved manifest paths.

    Returns:
        `0` for success or `2` when validation fails.

    Raises:
        SystemExit: If the action is invalid.
    """
    action_value = args.action
    try:
        action = action_value if isinstance(action_value, ManifestAction) else ManifestAction.from_str(action_value)
    # ignore JUSTIFIED: argparse enforces valid choices; this branch is defensive only
    except ValueError as exc:  # pragma: no cover - argparse prevents invalid choices
        raise SystemExit(str(exc)) from exc
    if action is ManifestAction.VALIDATE:
        return _handle_validate(args, context)
    if action is ManifestAction.SCHEMA:
        return _handle_schema(args)
    _raise_unknown_manifest_action(action)


__all__ = ["execute_manifest", "register_manifest_command"]
