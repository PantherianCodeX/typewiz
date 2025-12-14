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

from ratchetr.cli.helpers import (
    StdoutFormat,
    echo,
    infer_stdout_format_from_save_flag,
    parse_save_flag,
    register_save_flag,
    render_data,
)
from ratchetr.core.model_types import DataFormat
from ratchetr.engines.registry import describe_engines
from ratchetr.paths import OutputFormat

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ratchetr.cli.helpers import CLIContext
    from ratchetr.cli.types import SubparserCollection


def register_engines_command(
    subparsers: SubparserCollection,
    *,
    parents: Sequence[argparse.ArgumentParser] | None = None,
) -> None:
    """Attach the `ratchetr engines`command to the CLI.

    Args:
        subparsers: Top-level argparse subparser collection to register commands on.
        parents: Shared parent parsers carrying global options.
    """
    engines = subparsers.add_parser(
        "engines",
        help="Inspect discovered ratchetr engines",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        parents=parents or [],
    )
    engines_sub = engines.add_subparsers(dest="engines_action", required=True)

    engines_list = engines_sub.add_parser(
        "list",
        help="List registered engines",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        parents=parents or [],
    )
    register_save_flag(
        engines_list,
        flag="--save-as",
        dest="output",
        short_flag="-s",
        aliases=("--output",),
    )


def _handle_list(args: argparse.Namespace) -> int:
    descriptors = describe_engines()
    save_flag = parse_save_flag(
        getattr(args, "output", None),
        allowed_formats={OutputFormat.JSON},
    )
    base_stdout = StdoutFormat.from_str(getattr(args, "out", StdoutFormat.TEXT.value))
    stdout_format = infer_stdout_format_from_save_flag(args, base_stdout, save_flag=save_flag)
    fmt = DataFormat.JSON if stdout_format is StdoutFormat.JSON else DataFormat.TABLE
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
    if save_flag.provided:
        json_lines = render_data(payload, DataFormat.JSON)
        json_text = json_lines[0] if json_lines else ""
        for target in save_flag.targets:
            if target.path is None:
                continue
            target.path.parent.mkdir(parents=True, exist_ok=True)
            target.path.write_text(json_text + "\n", encoding="utf-8")
    return 0


def execute_engines(args: argparse.Namespace, _: CLIContext) -> int:
    """Execute the engines subcommand.

    Args:
        args: Parsed CLI namespace.

    Returns:
        `0`if the action completes successfully.

    Raises:
        SystemExit: If the requested action is unknown.
    """
    action_value = getattr(args, "engines_action", None)
    if action_value == "list":
        return _handle_list(args)
    msg = f"Unknown engines action '{action_value}'"
    raise SystemExit(msg)


__all__ = ["execute_engines", "register_engines_command"]
