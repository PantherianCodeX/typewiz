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

"""Cache management commands for the ratchetr CLI."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

from ratchetr.cli.helpers import echo, register_argument
from ratchetr.runtime import resolve_project_root

if TYPE_CHECKING:
    from ratchetr.cli.types import SubparserCollection


def register_cache_command(subparsers: SubparserCollection) -> None:
    """Attach the ``ratchetr cache`` command to the CLI.

    Args:
        subparsers: Top-level argparse subparser collection to register commands on.
    """
    cache = subparsers.add_parser(
        "cache",
        help="Inspect or clear ratchetr caches",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    cache_sub = cache.add_subparsers(dest="cache_action", required=True)

    clear = cache_sub.add_parser(
        "clear",
        help="Remove the on-disk cache directory",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    register_argument(
        clear,
        "--project-root",
        type=Path,
        default=None,
        help="Override project root discovery (default: auto-detected).",
    )
    register_argument(
        clear,
        "--path",
        type=Path,
        default=None,
        help="Explicit cache directory (default: <project>/.ratchetr_cache).",
    )


def _handle_clear(args: argparse.Namespace) -> int:
    project_root = resolve_project_root(getattr(args, "project_root", None))
    target: Path = (args.path if args.path is not None else project_root / ".ratchetr_cache").resolve()
    if not target.exists():
        echo(f"[ratchetr] cache directory not found at {target}; nothing to remove")
        return 0
    shutil.rmtree(target, ignore_errors=False)
    echo(f"[ratchetr] Cleared cache at {target}")
    return 0


def execute_cache(args: argparse.Namespace) -> int:
    """Execute the cache subcommand.

    Args:
        args: Parsed CLI namespace.

    Returns:
        ``0`` when the requested action completes successfully.

    Raises:
        SystemExit: If the action name is unrecognised.
    """
    action_value = getattr(args, "cache_action", None)
    if action_value == "clear":
        return _handle_clear(args)
    msg = f"Unknown cache action '{action_value}'"
    raise SystemExit(msg)


__all__ = ["execute_cache", "register_cache_command"]
