# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Property-based tests for Paths."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from hypothesis import HealthCheck, given, settings

from tests.property_based.strategies import path_parts
from typewiz.audit.paths import normalise_paths

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
