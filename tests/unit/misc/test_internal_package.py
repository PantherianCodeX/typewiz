# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Unit tests for Misc Internal Package."""

from __future__ import annotations

import importlib

import pytest

import typewiz._internal as internal

pytestmark = pytest.mark.unit


def test_internal_lazy_imports_cache_module() -> None:
    cache_mod = internal.cache
    assert cache_mod is internal.cache
    assert importlib.import_module("typewiz._internal.cache") is cache_mod


def test_internal_dir_and_invalid_attribute() -> None:
    listing = dir(internal)
    assert "cache" in listing
    with pytest.raises(AttributeError, match="has no attribute 'not_real'"):
        _ = internal.not_real
