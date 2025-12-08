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

"""Unit tests for the cache CLI command flows."""

from __future__ import annotations

from argparse import Namespace
from typing import TYPE_CHECKING

import pytest

from ratchetr.cli.commands import cache as cache_cmd

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = [pytest.mark.unit, pytest.mark.cli]


def test_handle_clear_removes_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    target = tmp_path / ".ratchetr_cache"
    target.mkdir()

    def fake_resolve_root(value: Path | None) -> Path:
        assert value is None
        return tmp_path

    monkeypatch.setattr(cache_cmd, "resolve_project_root", fake_resolve_root)
    args = Namespace(cache_action="clear", path=target, project_root=None)

    # Act
    exit_code = cache_cmd.execute_cache(args)

    # Assert
    assert exit_code == 0
    assert not target.exists()


def test_handle_clear_handles_missing_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    args = Namespace(cache_action="clear", path=tmp_path / "missing", project_root=None)

    def fake_root(_: object) -> Path:
        return tmp_path

    monkeypatch.setattr(cache_cmd, "resolve_project_root", fake_root)

    # Act
    exit_code = cache_cmd.execute_cache(args)

    # Assert
    assert exit_code == 0


def test_execute_cache_unknown_action() -> None:
    # Act / Assert
    with pytest.raises(SystemExit, match=r".*"):
        _ = cache_cmd.execute_cache(Namespace(cache_action="invalid"))
