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

"""Unit tests for scope resolution and canonicalization (ADR-0002)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ratchetr.audit.paths import canonicalize_scope

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = [pytest.mark.unit, pytest.mark.audit]


def test_canonicalize_scope_sorts_paths(tmp_path: Path) -> None:
    """Canonicalized scope is sorted for deterministic comparison."""
    result = canonicalize_scope(tmp_path, ["zebra", "apple", "middle"])
    assert result == ["apple", "middle", "zebra"]


def test_canonicalize_scope_deduplicates(tmp_path: Path) -> None:
    """Canonicalized scope removes duplicates."""
    result = canonicalize_scope(tmp_path, ["src", "tests", "src", "lib", "tests"])
    assert result == ["lib", "src", "tests"]


def test_canonicalize_scope_normalizes_posix(tmp_path: Path) -> None:
    """Canonicalized scope uses POSIX format."""
    # Even on Windows, paths should be POSIX
    result = canonicalize_scope(tmp_path, ["src\\foo", "tests/bar"])
    assert all("/" not in p or "\\" not in p for p in result)
    assert len(result) == 2


def test_canonicalize_scope_empty_input(tmp_path: Path) -> None:
    """Canonicalized scope handles empty input."""
    result = canonicalize_scope(tmp_path, [])
    assert result == []


def test_canonicalize_scope_relative_to_root(tmp_path: Path) -> None:
    """Canonicalized scope resolves paths relative to project root."""
    result = canonicalize_scope(tmp_path, ["./src", "tests"])
    # Both should be relative paths without leading ./
    assert all(not p.startswith("./") for p in result)
    assert "src" in result
    assert "tests" in result
