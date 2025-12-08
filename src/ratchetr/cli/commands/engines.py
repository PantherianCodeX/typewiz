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

"""Engine discovery helpers for the ratchetr CLI."""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING

from ratchetr.cli.helpers import echo, register_argument, render_data
from ratchetr.core.model_types import DataFormat
from ratchetr.engines.registry import describe_engines

if TYPE_CHECKING:
    from ratchetr.cli.types import SubparserCollection


def register_engines_command(subparsers: SubparserCollection) -> None:
    """Attach the ``ratchetr engines`` command to the CLI."""
    engines = subparsers.add_parser(
        "engines",
        help="Inspect discovered ratchetr engines",
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
    """Execute the engines subcommand.

    Args:
        args: Parsed CLI namespace.

    Returns:
        ``0`` if the action completes successfully.

    Raises:
        SystemExit: If the requested action is unknown.
    """
    action_value = getattr(args, "engines_action", None)
    if action_value == "list":
        return _handle_list(args)
    msg = f"Unknown engines action '{action_value}'"
    raise SystemExit(msg)


__all__ = ["execute_engines", "register_engines_command"]
