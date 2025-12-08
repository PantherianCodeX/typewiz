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

"""Property-based tests for Paths."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from hypothesis import HealthCheck, given, settings

from ratchetr.audit.paths import normalise_paths
from tests.property_based.strategies import path_parts

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.property


@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(parts=path_parts())
def test_h_normalise_paths_dedup_and_posix(parts: list[str], tmp_path: Path) -> None:
    # Build directories for each path under tmp_path
    raw_inputs: list[str] = []
    for p in parts:
        sub = p.strip("/") or "pkg"
        d = tmp_path / sub
        d.mkdir(parents=True, exist_ok=True)
        # include variants with trailing slashes
        raw_inputs.extend([sub, f"{sub}/"])

    result = normalise_paths(tmp_path, raw_inputs)
    # Deduplication: result length <= number of unique normalized inputs
    assert len(result) <= len({s.rstrip("/") for s in raw_inputs})
    # POSIX style and no trailing slashes
    for r in result:
        assert "\\" not in r
        assert not r.endswith("/")
