# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Tests for common override formatting helpers."""

from __future__ import annotations

from typewiz.common import override_utils


def test_format_override_inline_with_details() -> None:
    entry = {
        "path": "src/app.py",
        "profile": "strict",
        "pluginArgs": ["--foo"],
        "include": ["src"],
        "exclude": ["tests"],
    }
    inline = override_utils.format_override_inline(entry)
    assert "strict" in inline
    assert "args=" in inline


def test_format_overrides_block_falls_back_to_no_changes() -> None:
    entry = {"path": "src/app.py"}
    lines = override_utils.format_overrides_block([entry])
    assert "no explicit changes" in lines[0]


def test_format_overrides_block_includes_profile_and_args() -> None:
    entry = {
        "path": "src/app.py",
        "profile": "strict",
        "pluginArgs": ["--foo"],
    }
    lines = override_utils.format_overrides_block([entry])
    assert "profile=strict" in lines[0]
    assert "plugin args" in lines[0]
