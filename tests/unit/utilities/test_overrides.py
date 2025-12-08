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

"""Unit tests for Utilities Overrides."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pytest

from ratchetr.common.override_utils import (
    format_override_inline,
    format_overrides_block,
    get_override_components,
    override_detail_lines,
)

if TYPE_CHECKING:
    from ratchetr.core.model_types import OverrideEntry

pytestmark = pytest.mark.unit


def test_get_override_components_normalises_values() -> None:
    entry = cast(
        "OverrideEntry",
        {
            "path": "src",
            "profile": "strict",
            "pluginArgs": ["--warn", "--warn"],
            "include": ["apps", "apps"],
            "exclude": ["tests"],
        },
    )
    path, profile, plugin_args, include, exclude = get_override_components(entry)
    assert path == "src"
    assert profile == "strict"
    assert plugin_args == ["--warn"]
    assert include == ["apps"]
    assert exclude == ["tests"]


def test_format_override_inline_includes_details() -> None:
    entry = cast(
        "OverrideEntry",
        {
            "path": "src",
            "profile": "strict",
            "pluginArgs": ["--warn"],
            "include": ["apps"],
            "exclude": ["tests"],
        },
    )
    formatted = format_override_inline(entry)
    assert formatted.startswith("src(")
    assert "profile=strict" in formatted
    assert "args=--warn" in formatted
    assert "include=apps" in formatted
    assert "exclude=tests" in formatted


def test_format_override_inline_handles_missing_details() -> None:
    entry = cast("OverrideEntry", {"path": "pkg"})
    assert format_override_inline(entry) == "pkg"


def test_format_overrides_block_outputs_list() -> None:
    entries: list[OverrideEntry] = [
        cast("OverrideEntry", {"path": "apps", "pluginArgs": ["--foo"]}),
        cast("OverrideEntry", {"path": "pkg", "include": ["."], "exclude": ["legacy"]}),
    ]
    lines = format_overrides_block(entries)
    assert lines[0].startswith("  - `apps`")
    assert "plugin args: `--foo`" in lines[0]
    assert "include: `.`" in lines[1]
    assert "exclude: `legacy`" in lines[1]


def test_override_detail_lines_reports_defaults() -> None:
    entry = cast("OverrideEntry", {"path": "src"})
    path, details = override_detail_lines(entry)
    assert path == "src"
    assert details == ["no explicit changes"]
