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

"""Tests for :mod:`scripts.make_find` search helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from scripts import make_find

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path


# ---------------------------------------------------------------------------
# Fixtures / shared test data
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_makefile_text() -> str:
    """Return a small Makefile snippet for exercising search semantics.

    The structure is intentionally similar (but smaller) than the real
    Makefile, with three sections:

    * Tests
    * Cleaning
    * Packaging

    The commands are chosen to exercise both OR and AND semantics,
    especially around ``test`` / ``clean`` combinations.
    """
    return (
        'HELP_GROUP_FORMAT := "\\nGROUP:%s\\n"\n'
        'HELP_CMD_FORMAT   := "CMD:%s:%s\\n"\n'
        "\n"
        "##@ Tests\n"
        "test: ## Run tests\n"
        "test.clean: ## Clean tests\n"
        "\n"
        "##@ Cleaning\n"
        "clean: ## Clean all\n"
        "clean.test: ## Clean test artifacts\n"
        "clean.pytest: ## Clean pytest cache\n"
        "\n"
        "##@ Packaging\n"
        "package.install-test: ## Install test wheel\n"
        "package.clean: ## Clean build artifacts\n"
    )


@pytest.fixture
def sample_makefile_path(tmp_path: Path, sample_makefile_text: str) -> Path:
    """Write `sample_makefile_text` to a temporary Makefile path.

    Returns:
        Path to the written Makefile in a temporary directory.
    """
    path = tmp_path / "Makefile"
    path.write_text(sample_makefile_text, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Unit tests: helpers
# ---------------------------------------------------------------------------


def test_slugify_label_basic() -> None:
    """_slugify_label should normalize labels predictably."""
    assert make_find._slugify_label("Tests") == "tests"
    assert make_find._slugify_label("Lint & Format") == "lint.format"
    assert make_find._slugify_label("  Fancy-Name  ") == "fancy.name"


def test_decode_from_make_found_and_decoded(sample_makefile_text: str) -> None:
    """decode_from_make should locate and decode escaped Makefile strings."""
    lines = sample_makefile_text.splitlines()
    group_fmt = make_find.decode_from_make(lines, "HELP_GROUP_FORMAT")
    cmd_fmt = make_find.decode_from_make(lines, "HELP_CMD_FORMAT")

    assert group_fmt == "\nGROUP:%s\n"
    assert cmd_fmt == "CMD:%s:%s\n"


def test_decode_from_make_default_when_missing(sample_makefile_text: str) -> None:
    """decode_from_make should return the default when a variable is missing."""
    lines = sample_makefile_text.splitlines()
    default = "<default>"
    value = make_find.decode_from_make(lines, "NON_EXISTENT_VAR", default=default)
    assert value == default


def test_decode_from_make_raises_without_default(sample_makefile_text: str) -> None:
    """decode_from_make should raise SystemExit if missing and no default."""
    lines = sample_makefile_text.splitlines()
    with pytest.raises(SystemExit) as exc_info:
        _ = make_find.decode_from_make(lines, "NON_EXISTENT_VAR")

    assert "Missing definition for NON_EXISTENT_VAR" in str(exc_info.value)


def test_collect_sections_parses_sections_and_commands(
    sample_makefile_text: str,
) -> None:
    """collect_sections should build section descriptors and command mapping."""
    lines = sample_makefile_text.splitlines()
    sections, commands = make_find.collect_sections(lines)

    # Section slugs and labels
    assert sections == [
        ("tests", "Tests"),
        ("cleaning", "Cleaning"),
        ("packaging", "Packaging"),
    ]

    # Commands per section
    assert [cmd[0] for cmd in commands["tests"]] == ["test", "test.clean"]
    assert [cmd[0] for cmd in commands["cleaning"]] == [
        "clean",
        "clean.test",
        "clean.pytest",
    ]
    assert [cmd[0] for cmd in commands["packaging"]] == [
        "package.install-test",
        "package.clean",
    ]


def test_parse_terms_or_and_split() -> None:
    """_parse_terms should split raw tokens into OR and AND groups."""
    raw: Sequence[str] = ["lint", "python+3.11", "test+clean"]
    or_terms, and_terms = make_find._parse_terms(raw)

    assert or_terms == ["lint"]
    # Order is preserved across splits
    assert and_terms == ["python", "3.11", "test", "clean"]


# ---------------------------------------------------------------------------
# Unit tests: label-oriented mode
# ---------------------------------------------------------------------------


def test_labels_only_matches_or_semantics(sample_makefile_text: str) -> None:
    """labels-only mode with OR should match heading+name text per command.

    Query: 'test' (OR-only) should return any command whose heading+name
    text contains 'test', grouped under their section labels.
    """
    lines = sample_makefile_text.splitlines()
    sections, commands = make_find.collect_sections(lines)
    or_terms, and_terms = make_find._parse_terms(["test"])

    matches = make_find._labels_only_matches(sections, commands, or_terms, and_terms)

    # We expect all the commands whose name or section context contains 'test'.
    assert "Tests" in matches
    assert {name for name, _ in matches["Tests"]} == {"test", "test.clean"}

    assert "Cleaning" in matches
    assert {name for name, _ in matches["Cleaning"]} == {
        "clean.test",
        "clean.pytest",
    }

    # Packaging has a 'package.install-test' command that should match.
    assert "Packaging" in matches
    assert {name for name, _ in matches["Packaging"]} == {"package.install-test"}


def test_labels_only_matches_and_semantics(sample_makefile_text: str) -> None:
    """labels-only mode with AND should require all '+' terms in heading+name.

    Query: 'test+clean' should match only commands whose combined
    '<slug> <label> <name>' text contains both 'test' and 'clean'.
    """
    lines = sample_makefile_text.splitlines()
    sections, commands = make_find.collect_sections(lines)
    or_terms, and_terms = make_find._parse_terms(["test+clean"])

    matches = make_find._labels_only_matches(sections, commands, or_terms, and_terms)

    # Expect exactly the commands where both 'test' and 'clean' appear
    # in '<slug> <label> <name>'.
    assert "Tests" in matches
    assert {name for name, _ in matches["Tests"]} == {"test.clean"}

    assert "Cleaning" in matches
    assert {name for name, _ in matches["Cleaning"]} == {
        "clean.test",
        "clean.pytest",  # 'pytest' contains 'test'
    }

    # Packaging only has 'package.install-test' and 'package.clean' separately;
    # neither combined heading+name contains both 'test' and 'clean'.
    assert "Packaging" not in matches


# ---------------------------------------------------------------------------
# Unit tests: full-text mode
# ---------------------------------------------------------------------------


def test_fulltext_matches_heading_match_brings_full_group(
    sample_makefile_text: str,
) -> None:
    """full-text mode should include entire groups when heading matches.

    Query: 'Tests' should cause the 'Tests' section heading to match,
    and therefore all of its commands should be returned.
    """
    lines = sample_makefile_text.splitlines()
    sections, commands = make_find.collect_sections(lines)
    or_terms, and_terms = make_find._parse_terms(["Tests"])

    matches = make_find._fulltext_matches(sections, commands, or_terms, and_terms)

    assert "Tests" in matches
    assert {name for name, _ in matches["Tests"]} == {"test", "test.clean"}

    # Other sections should not match on this query.
    assert "Cleaning" not in matches
    assert "Packaging" not in matches


def test_fulltext_matches_command_only_when_heading_does_not_match(
    sample_makefile_text: str,
) -> None:
    """full-text mode should return only matching commands when heading fails.

    Query: 'install' should not match any section headings, but should
    match the 'package.install-test' command by name/description.
    """
    lines = sample_makefile_text.splitlines()
    sections, commands = make_find.collect_sections(lines)
    or_terms, and_terms = make_find._parse_terms(["install"])

    matches = make_find._fulltext_matches(sections, commands, or_terms, and_terms)

    assert "Packaging" in matches
    assert {name for name, _ in matches["Packaging"]} == {"package.install-test"}

    # No other sections should have matching commands for 'install'.
    assert "Tests" not in matches
    assert "Cleaning" not in matches


# ---------------------------------------------------------------------------
# Integration-ish: render_help and CLI
# ---------------------------------------------------------------------------


def test_render_help_fulltext_uses_makefile_formats(
    sample_makefile_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """render_help in full-text mode should honour HELP_*_FORMAT values."""
    exit_code = make_find.render_help(
        makefile_path=sample_makefile_path,
        labels_only=False,
        terms=["test"],
    )
    captured = capsys.readouterr().out

    assert exit_code == 0
    # Group headings should use the decoded GROUP format.
    assert "GROUP:Tests" in captured
    # Commands should use the decoded CMD format.
    assert "CMD:test:Run tests" in captured


def test_render_help_labels_only_and_semantics(
    sample_makefile_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """render_help in labels-only mode should apply AND semantics.

    Query 'test+clean' should yield only commands whose heading+name
    text contains both 'test' and 'clean'.
    """
    exit_code = make_find.render_help(
        makefile_path=sample_makefile_path,
        labels_only=True,
        terms=["test+clean"],
    )
    captured = capsys.readouterr().out

    assert exit_code == 0

    # The Tests section should show only 'test.clean'.
    assert "GROUP:Tests" in captured
    assert "CMD:test.clean:Clean tests" in captured
    assert "CMD:test:Run tests" not in captured

    # The Cleaning section should show 'clean.test' and 'clean.pytest'.
    assert "GROUP:Cleaning" in captured
    assert "CMD:clean.test:Clean test artifacts" in captured
    assert "CMD:clean.pytest:Clean pytest cache" in captured

    # Packaging should not appear for this AND query.
    assert "GROUP:Packaging" not in captured


def test_render_help_no_matches_returns_nonzero(
    sample_makefile_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """render_help should return 1 and print a message when no matches exist."""
    exit_code = make_find.render_help(
        makefile_path=sample_makefile_path,
        labels_only=False,
        terms=["completely-unmatched-term"],
    )
    captured = capsys.readouterr().out

    assert exit_code == 1
    assert "No matching sections or commands." in captured


def test_main_raises_systemexit_when_makefile_missing(tmp_path: Path) -> None:
    """Entrypoint main should raise SystemExit when the requested Makefile does not exist."""
    missing = tmp_path / "DoesNotExist.Makefile"
    assert not missing.exists()

    with pytest.raises(SystemExit) as exc_info:
        _ = make_find.main(["--makefile", str(missing), "lint"])

    message = str(exc_info.value)
    assert "Makefile not found" in message
    assert str(missing) in message


def test_main_returns_zero_on_success(
    sample_makefile_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Entrypoint main should return 0 on successful search."""
    exit_code = make_find.main(
        ["--makefile", str(sample_makefile_path), "test"],
    )
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "GROUP:Tests" in output
    assert "CMD:test:Run tests" in output
