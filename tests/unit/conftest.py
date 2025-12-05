# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Fixtures shared across all unit tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.fixtures.builders import TestDataBuilder

if TYPE_CHECKING:
    from typewiz.core.summary_types import SummaryData


@pytest.fixture(scope="session")
def test_data_builder() -> TestDataBuilder:
    """Provide a reusable test data builder for unit tests.

    Returns:
        Shared ``TestDataBuilder`` instance.
    """
    return TestDataBuilder()


@pytest.fixture
def sample_summary(test_data_builder: TestDataBuilder) -> SummaryData:
    """Return the canonical summary payload used across unit tests."""
    return test_data_builder.build_sample_summary()
