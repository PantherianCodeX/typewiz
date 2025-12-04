# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

from __future__ import annotations

from typing import cast

import pytest

from typewiz.common.override_utils import (
    format_override_inline,
    format_overrides_block,
    get_override_components,
    override_detail_lines,
)
from typewiz.core.model_types import OverrideEntry

pytestmark = pytest.mark.unit


def test_get_override_components_normalises_values() -> None:
    entry = cast(
        OverrideEntry,
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
        OverrideEntry,
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
    entry = cast(OverrideEntry, {"path": "pkg"})
    assert format_override_inline(entry) == "pkg"


def test_format_overrides_block_outputs_list() -> None:
    entries: list[OverrideEntry] = [
        cast(OverrideEntry, {"path": "apps", "pluginArgs": ["--foo"]}),
        cast(OverrideEntry, {"path": "pkg", "include": ["."], "exclude": ["legacy"]}),
    ]
    lines = format_overrides_block(entries)
    assert lines[0].startswith("  - `apps`")
    assert "plugin args: `--foo`" in lines[0]
    assert "include: `.`" in lines[1]
    assert "exclude: `legacy`" in lines[1]


def test_override_detail_lines_reports_defaults() -> None:
    entry = cast(OverrideEntry, {"path": "src"})
    path, details = override_detail_lines(entry)
    assert path == "src"
    assert details == ["no explicit changes"]
