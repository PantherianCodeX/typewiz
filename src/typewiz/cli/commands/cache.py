# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Cache management commands for the Typewiz CLI."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Protocol

from typewiz.cli.helpers import echo, register_argument
from typewiz.runtime import resolve_project_root


class SubparserRegistry(Protocol):
    def add_parser(self, *args: object, **kwargs: object) -> argparse.ArgumentParser:
        """Register a CLI subcommand on an argparse subparser collection."""
        ...  # pragma: no cover - Protocol helper


def register_cache_command(subparsers: SubparserRegistry) -> None:
    """Attach the ``typewiz cache`` command to the CLI."""
    cache = subparsers.add_parser(
        "cache",
        help="Inspect or clear Typewiz caches",
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
        help="Explicit cache directory (default: <project>/.typewiz_cache).",
    )


def _handle_clear(args: argparse.Namespace) -> int:
    project_root = resolve_project_root(getattr(args, "project_root", None))
    target: Path = (args.path if args.path is not None else (project_root / ".typewiz_cache")).resolve()
    if not target.exists():
        echo(f"[typewiz] cache directory not found at {target}; nothing to remove")
        return 0
    shutil.rmtree(target, ignore_errors=False)
    echo(f"[typewiz] Cleared cache at {target}")
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
