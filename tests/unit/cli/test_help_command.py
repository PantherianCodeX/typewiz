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

"""Unit tests for the CLI help command topics."""

from __future__ import annotations

from argparse import Namespace
from typing import TYPE_CHECKING

import pytest

from ratchetr.cli.commands.help import execute_help

if TYPE_CHECKING:
    from pathlib import Path

    from ratchetr.cli.helpers import CLIContext

pytestmark = [pytest.mark.unit, pytest.mark.cli]


def _write_topic(topics_dir: Path, name: str, content: str) -> None:
    file_path = topics_dir / f"{name}.md"
    _ = file_path.write_text(content, encoding="utf-8")


def test_execute_help_lists_topics(
    tmp_path: Path,
    cli_context: CLIContext,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Arrange
    topics_dir = tmp_path / "topics"
    topics_dir.mkdir()
    _write_topic(topics_dir, "overview", "# Overview\n")
    _write_topic(topics_dir, "ratchet_basics", "# Ratchet\n")
    args = Namespace(topic=None, topics_dir=topics_dir)

    # Act
    exit_code = execute_help(args, cli_context)

    # Assert
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "[ratchetr] Available help topics:" in output
    assert "overview" in output
    # Underscores should be normalized to hyphenated topic names.
    assert "ratchet-basics" in output


def test_execute_help_unknown_topic_lists_choices(
    tmp_path: Path,
    cli_context: CLIContext,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Arrange
    topics_dir = tmp_path / "topics"
    topics_dir.mkdir()
    _write_topic(topics_dir, "overview", "# Overview\n")
    args = Namespace(topic="missing", topics_dir=topics_dir)

    # Act
    exit_code = execute_help(args, cli_context)

    # Assert
    assert exit_code == 2
    captured = capsys.readouterr().out
    assert "[ratchetr] Unknown topic 'missing'." in captured
    assert "overview" in captured


def test_execute_help_renders_topic_content(
    tmp_path: Path,
    cli_context: CLIContext,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Arrange
    topics_dir = tmp_path / "topics"
    topics_dir.mkdir()
    content = "# Ratchet\n\nDetails"
    _write_topic(topics_dir, "ratchet", content)
    args = Namespace(topic="ratchet", topics_dir=topics_dir)

    # Act
    exit_code = execute_help(args, cli_context)

    # Assert
    assert exit_code == 0
    captured = capsys.readouterr().out
    assert content in captured
