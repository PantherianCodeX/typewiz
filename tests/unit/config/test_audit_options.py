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

"""Unit tests for Config Audit Options."""

from __future__ import annotations

import pytest

from ratchetr.audit.options import normalise_category_mapping, prepare_category_mapping

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
