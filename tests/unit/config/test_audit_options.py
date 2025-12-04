# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Unit tests for Config Audit Options."""

from __future__ import annotations

import pytest

from typewiz.audit.options import normalise_category_mapping, prepare_category_mapping

pytestmark = pytest.mark.unit


def test_prepare_category_mapping_filters_invalid_keys() -> None:
    mapping = prepare_category_mapping(
        {
            "unknownChecks": [" foo ", "foo", ""],
            "optionalChecks": ["opt"],
            "custom": ["bar"],
            "": ["baz"],
        },
    )
    assert mapping is not None
    assert set(mapping.keys()) == {"unknownChecks", "optionalChecks"}
    assert list(mapping["unknownChecks"]) == ["foo", "foo"]


def test_normalise_category_mapping_dedupes_and_orders() -> None:
    normalised = normalise_category_mapping(
        {
            "optionalChecks": ["Opt", "opt"],
            "unknownChecks": ["Foo", "bar", "foo"],
        },
    )
    assert list(normalised) == ["optionalChecks", "unknownChecks"]
    assert normalised["optionalChecks"] == ["Opt"]
    assert normalised["unknownChecks"] == ["Foo", "bar"]
