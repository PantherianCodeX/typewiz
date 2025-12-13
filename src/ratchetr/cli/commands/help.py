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

"""Topic-based help command for the ratchetr CLI."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import TYPE_CHECKING

from ratchetr.cli.helpers import echo, register_argument

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ratchetr.cli.helpers import CLIContext
    from ratchetr.cli.types import SubparserCollection

_TOPICS_ROOT = Path(__file__).resolve().parents[4] / "docs" / "cli" / "topics"


def register_help_command(
    subparsers: SubparserCollection,
    *,
    parents: Sequence[argparse.ArgumentParser] | None = None,
) -> None:
    """Register `ratchetr help`with topic support.

    Args:
        subparsers: Top-level argparse subparser collection to register commands on.
        parents: Shared parent parsers carrying global options.
    """
    help_parser = subparsers.add_parser(
        "help",
        help="Show CLI topic documentation",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        parents=parents or [],
    )
    register_argument(
        help_parser,
        "topic",
        nargs="?",
        default=None,
        help="Topic name to display (omit to list topics).",
    )
    register_argument(
        help_parser,
        "--topics-dir",
        type=Path,
        default=None,
        help="Override the topics directory (primarily for testing).",
    )


def _discover_topics(root: Path) -> dict[str, Path]:
    topics: dict[str, Path] = {}
    if not root.exists():
        return topics
    for path in sorted(root.glob("*.md")):
        topics[path.stem.replace("_", "-")] = path
    return topics


def _read_topic(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _render_topics_list(topics: dict[str, Path]) -> None:
    if not topics:
        echo("[ratchetr] No help topics available.")
        return
    echo("[ratchetr] Available help topics:")
    for name in sorted(topics):
        echo(f"  - {name}")
    echo("")
    echo("Use `ratchetr help <topic>` to view a topic.")


def execute_help(args: argparse.Namespace, _: CLIContext) -> int:
    """Execute the `ratchetr help`command.

    Args:
        args: Parsed CLI namespace containing optional topic data.

    Returns:
        `0`on success or `2`if the requested topic is unknown.
    """
    root = args.topics_dir or _TOPICS_ROOT
    topics = _discover_topics(root)
    topic = args.topic

    if topic is None:
        _render_topics_list(topics)
        return 0

    topic_key = topic.strip().lower().replace("_", "-")
    if topic_key not in topics:
        echo(f"[ratchetr] Unknown topic '{topic_key}'.")
        _render_topics_list(topics)
        return 2

    echo(_read_topic(topics[topic_key]))
    return 0


__all__ = ["execute_help", "register_help_command"]
