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

"""Unit tests for Config Validation."""

from __future__ import annotations

import math

import pytest

from ratchetr.config.validation import (
    coerce_float,
    coerce_int,
    coerce_mapping,
    coerce_object_list,
    coerce_optional_str,
    coerce_str,
    coerce_str_list,
    ensure_optional_str_list,
    require_non_negative_int,
)

pytestmark = pytest.mark.unit


def test_coerce_str_handles_non_string() -> None:
    assert coerce_str(None, default="fallback") == "fallback"
    assert coerce_str(123) == "123"
    assert coerce_str("value") == "value"


def test_coerce_int_parses_values() -> None:
    assert coerce_int(value=True) == 1
    assert coerce_int("42") == 42
    assert coerce_int("invalid", default=7) == 7


def test_coerce_optional_str_handles_empty() -> None:
    assert coerce_optional_str(None) is None
    assert coerce_optional_str("") is None
    assert coerce_optional_str("value") == "value"


def test_require_non_negative_int_rejects_negative() -> None:
    assert require_non_negative_int("6", context="count") == 6
    with pytest.raises(ValueError, match="count must be non-negative"):
        _ = require_non_negative_int(-5, context="count")


def test_coerce_float_parses_values() -> None:
    result = coerce_float("3.14")
    assert abs(result - math.pi) < 1e-9
    assert coerce_float("bad", default=1.5) == 1.5


def test_coerce_mapping_filters_keys() -> None:
    result = coerce_mapping({"a": 1, 2: "b"})
    assert result == {"a": 1, "2": "b"}
    assert coerce_mapping("nope") == {}


def test_coerce_object_list_filters_sequences() -> None:
    assert coerce_object_list(["a", "b"]) == ["a", "b"]
    assert coerce_object_list("abc") == []
    assert coerce_object_list(None) == []


def test_coerce_str_list_returns_strings() -> None:
    assert coerce_str_list([1, "x"]) == ["1", "x"]
    assert coerce_str_list("xx") == []


def test_ensure_optional_str_list_roundtrip() -> None:
    assert ensure_optional_str_list(["a", 2]) == ["a", "2"]
    assert ensure_optional_str_list([]) is None
    assert ensure_optional_str_list(None) is None
