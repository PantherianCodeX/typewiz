# Copyright (c) 2024 PantherianCodeX

"""Unit tests for CLI helper utilities."""

from __future__ import annotations

import pytest

from typewiz.cli_helpers import (
    collect_profile_args,
    parse_comma_separated,
    parse_int_mapping,
    parse_key_value_entries,
    render_data_structure,
)
from typewiz.model_types import DataFormat


def test_parse_comma_separated_strips_entries() -> None:
    assert parse_comma_separated("foo, bar ,,,baz") == ["foo", "bar", "baz"]
    assert parse_comma_separated(None) == []


def test_parse_key_value_entries_returns_pairs() -> None:
    pairs = parse_key_value_entries(["runner=strict", "mypy = baseline"], argument="--profile")
    assert pairs == [("runner", "strict"), ("mypy", "baseline")]


def test_parse_key_value_entries_rejects_invalid() -> None:
    with pytest.raises(SystemExit):
        _ = parse_key_value_entries(["novalue"], argument="--profile")


def test_parse_int_mapping_converts_to_ints() -> None:
    mapping = parse_int_mapping(["errors=1", "warnings=0"], argument="--target")
    assert mapping == {"errors": 1, "warnings": 0}


def test_parse_int_mapping_rejects_non_int() -> None:
    with pytest.raises(SystemExit):
        _ = parse_int_mapping(["errors=abc"], argument="--target")


def test_collect_profile_args_uses_helper() -> None:
    result = collect_profile_args(["pyright=baseline"])
    assert result == {"pyright": "baseline"}


def test_render_data_structure_accepts_enum() -> None:
    rows = render_data_structure({"key": "value"}, DataFormat.TABLE)
    assert rows[0].startswith("key")
