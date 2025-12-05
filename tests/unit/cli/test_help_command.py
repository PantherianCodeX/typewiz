# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Unit tests for the CLI help command topics."""

from __future__ import annotations

from argparse import Namespace
from typing import TYPE_CHECKING

import pytest

from typewiz.cli.commands.help import execute_help

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = [pytest.mark.unit, pytest.mark.cli]


def _write_topic(topics_dir: Path, name: str, content: str) -> None:
    file_path = topics_dir / f"{name}.md"
    _ = file_path.write_text(content, encoding="utf-8")


def test_execute_help_lists_topics(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Arrange
    topics_dir = tmp_path / "topics"
    topics_dir.mkdir()
    _write_topic(topics_dir, "overview", "# Overview\n")
    _write_topic(topics_dir, "ratchet_basics", "# Ratchet\n")
    args = Namespace(topic=None, topics_dir=topics_dir)

    # Act
    exit_code = execute_help(args)

    # Assert
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "[typewiz] Available help topics:" in output
    assert "overview" in output
    # Underscores should be normalised to hyphenated topic names.
    assert "ratchet-basics" in output


def test_execute_help_unknown_topic_lists_choices(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Arrange
    topics_dir = tmp_path / "topics"
    topics_dir.mkdir()
    _write_topic(topics_dir, "overview", "# Overview\n")
    args = Namespace(topic="missing", topics_dir=topics_dir)

    # Act
    exit_code = execute_help(args)

    # Assert
    assert exit_code == 2
    captured = capsys.readouterr().out
    assert "[typewiz] Unknown topic 'missing'." in captured
    assert "overview" in captured


def test_execute_help_renders_topic_content(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Arrange
    topics_dir = tmp_path / "topics"
    topics_dir.mkdir()
    content = "# Ratchet\n\nDetails"
    _write_topic(topics_dir, "ratchet", content)
    args = Namespace(topic="ratchet", topics_dir=topics_dir)

    # Act
    exit_code = execute_help(args)

    # Assert
    assert exit_code == 0
    captured = capsys.readouterr().out
    assert content in captured
