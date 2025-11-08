from __future__ import annotations

import importlib

import pytest

import typewiz._internal as internal


def test_internal_lazy_imports_cache_module() -> None:
    cache_mod = internal.__getattr__("cache")
    assert cache_mod is internal.__getattr__("cache")
    assert importlib.import_module("typewiz._internal.cache") is cache_mod


def test_internal_dir_and_invalid_attribute() -> None:
    listing = dir(internal)
    assert "cache" in listing
    with pytest.raises(AttributeError):
        _ = internal.__getattr__("not_real")
