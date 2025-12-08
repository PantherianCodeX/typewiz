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

"""Property-based tests for Enums."""

from __future__ import annotations

import pytest
from hypothesis import given

from ratchetr.core.model_types import SeverityLevel
from tests.property_based.strategies import arbitrary_cli_noise

pytestmark = pytest.mark.property


@given(arbitrary_cli_noise())
def test_severity_level_coerce_falls_back_to_information(noise: object) -> None:
    result = SeverityLevel.coerce(noise)
    assert isinstance(result, SeverityLevel)
