# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Property-based tests for Enums."""

from __future__ import annotations

import pytest
from hypothesis import given

from tests.property_based.strategies import arbitrary_cli_noise
from typewiz.core.model_types import SeverityLevel

pytestmark = pytest.mark.property


@given(arbitrary_cli_noise())
def test_severity_level_coerce_falls_back_to_information(noise: object) -> None:
    result = SeverityLevel.coerce(noise)
    assert isinstance(result, SeverityLevel)
