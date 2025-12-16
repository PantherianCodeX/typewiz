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

"""Unit tests for Misc Internal Package."""

from __future__ import annotations

import importlib

import pytest

import ratchetr._infra as internal

pytestmark = pytest.mark.unit


def test_infra_lazy_imports_cache_module() -> None:
    cache_mod = internal.cache
    assert cache_mod is internal.cache
    assert importlib.import_module("ratchetr._infra.cache") is cache_mod


def test_infra_dir_and_invalid_attribute() -> None:
    listing = dir(internal)
    assert "cache" in listing
    with pytest.raises(AttributeError, match="has no attribute 'not_real'"):
        _ = internal.not_real
