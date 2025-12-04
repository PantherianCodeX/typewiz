# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""CLI-specific fixtures shared across unit tests."""

from __future__ import annotations

import pytest

from tests.fixtures.builders import TestDataBuilder
from typewiz.core.summary_types import SummaryData
from typewiz.core.types import RunResult


@pytest.fixture
def cli_summary(test_data_builder: TestDataBuilder) -> SummaryData:
    """Provide a reusable sample summary for CLI helper tests."""
    return test_data_builder.build_cli_summary()


@pytest.fixture
def cli_run_result(test_data_builder: TestDataBuilder) -> RunResult:
    """Provide a representative RunResult for CLI helper tests."""
    return test_data_builder.build_cli_run_result()
