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

"""Tests for generic precedence chain resolution."""

from pathlib import Path

from ratchetr._infra.precedence import resolve_with_precedence


def test_resolve_with_precedence_cli_wins() -> None:
    """CLI value has highest precedence."""
    result = resolve_with_precedence(
        cli_value=["src"],
        env_value=["lib"],
        config_value=["pkg"],
        default=["."],
    )
    assert result == ["src"]


def test_resolve_with_precedence_env_when_no_cli() -> None:
    """Environment value wins when CLI is None."""
    result = resolve_with_precedence(
        cli_value=None,
        env_value=["lib"],
        config_value=["pkg"],
        default=["."],
    )
    assert result == ["lib"]


def test_resolve_with_precedence_config_when_no_cli_env() -> None:
    """Config value wins when CLI and env are None."""
    result = resolve_with_precedence(
        cli_value=None,
        env_value=None,
        config_value=["pkg"],
        default=["."],
    )
    assert result == ["pkg"]


def test_resolve_with_precedence_default_when_all_none() -> None:
    """Default value used when all others are None."""
    result = resolve_with_precedence(
        cli_value=None,
        env_value=None,
        config_value=None,
        default=["."],
    )
    assert result == ["."]


def test_resolve_with_precedence_empty_list_cli() -> None:
    """Empty list from CLI is treated as a value (not None)."""
    result = resolve_with_precedence(
        cli_value=[],
        env_value=["lib"],
        config_value=["pkg"],
        default=["."],
    )
    assert result == []


def test_resolve_with_precedence_with_strings() -> None:
    """Works with string values."""
    result = resolve_with_precedence(
        cli_value="cli_path",
        env_value="env_path",
        config_value="config_path",
        default="default_path",
    )
    assert result == "cli_path"


def test_resolve_with_precedence_with_paths() -> None:
    """Works with Path values."""
    result = resolve_with_precedence(
        cli_value=Path("/cli"),
        env_value=Path("/env"),
        config_value=Path("/config"),
        default=Path("/default"),
    )
    assert result == Path("/cli")
