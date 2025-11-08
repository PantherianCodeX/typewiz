# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Topic-based help command for the Typewiz CLI."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Protocol

from ..helpers import echo, register_argument

_TOPICS_ROOT = Path(__file__).resolve().parents[4] / "docs" / "cli" / "topics"


class SubparserRegistry(Protocol):
    def add_parser(
        self, *args: Any, **kwargs: Any
    ) -> argparse.ArgumentParser: ...  # pragma: no cover - Protocol


def register_help_command(subparsers: SubparserRegistry) -> None:
    """Register ``typewiz help`` with topic support."""
    help_parser = subparsers.add_parser(
        "help",
        help="Show CLI topic documentation",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
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
        echo("[typewiz] No help topics available.")
        return
    echo("[typewiz] Available help topics:")
    for name in sorted(topics):
        echo(f"  - {name}")
    echo("")
    echo("Use `typewiz help <topic>` to view a topic.")


def execute_help(args: argparse.Namespace) -> int:
    """Execute the ``typewiz help`` command."""
    root = args.topics_dir or _TOPICS_ROOT
    topics = _discover_topics(root)
    topic = args.topic

    if topic is None:
        _render_topics_list(topics)
        return 0

    topic_key = topic.strip().lower().replace("_", "-")
    if topic_key not in topics:
        echo(f"[typewiz] Unknown topic '{topic_key}'.")
        _render_topics_list(topics)
        return 2

    echo(_read_topic(topics[topic_key]))
    return 0


__all__ = ["execute_help", "register_help_command"]
