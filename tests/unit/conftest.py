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

"""Fixtures shared across all unit tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.fixtures.builders import TestDataBuilder

if TYPE_CHECKING:
    from ratchetr.core.summary_types import SummaryData


@pytest.fixture(scope="session")
def test_data_builder() -> TestDataBuilder:
    """Provide a reusable test data builder for unit tests.

    Returns:
        Shared `TestDataBuilder`instance.
    """
    return TestDataBuilder()


@pytest.fixture
def sample_summary(test_data_builder: TestDataBuilder) -> SummaryData:
    """Return the canonical summary payload used across unit tests."""
    return test_data_builder.build_sample_summary()
