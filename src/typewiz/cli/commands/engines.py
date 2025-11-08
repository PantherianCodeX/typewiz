# Copyright (c) 2024 PantherianCodeX
"""Engine discovery helpers for the Typewiz CLI."""

from __future__ import annotations

import argparse
from typing import Any, Protocol

from typewiz.engines.registry import describe_engines
from typewiz.model_types import DataFormat

from ..helpers import echo, register_argument, render_data


class SubparserRegistry(Protocol):
    def add_parser(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> argparse.ArgumentParser: ...  # pragma: no cover - Protocol helper


def register_engines_command(subparsers: SubparserRegistry) -> None:
    """Attach the ``typewiz engines`` command to the CLI."""
    engines = subparsers.add_parser(
        "engines",
        help="Inspect discovered Typewiz engines",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    engines_sub = engines.add_subparsers(dest="engines_action", required=True)

    list_cmd = engines_sub.add_parser(
        "list",
        help="List registered engines",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    register_argument(
        list_cmd,
        "--format",
        choices=[fmt.value for fmt in DataFormat],
        default=DataFormat.TABLE.value,
        help="Output format for the engine listing.",
    )


def _handle_list(args: argparse.Namespace) -> int:
    descriptors = describe_engines()
    fmt = DataFormat.from_str(getattr(args, "format", DataFormat.TABLE.value))
    payload = [
        {
            "name": str(descriptor.name),
            "module": descriptor.module,
            "class": descriptor.qualified_name,
            "origin": descriptor.origin,
        }
        for descriptor in descriptors
    ]
    for line in render_data(payload, fmt):
        echo(line)
    return 0


def execute_engines(args: argparse.Namespace) -> int:
    """Execute the engines subcommand."""
    action_value = getattr(args, "engines_action", None)
    if action_value == "list":
        return _handle_list(args)
    raise SystemExit(f"Unknown engines action '{action_value}'")


__all__ = ["execute_engines", "register_engines_command"]
