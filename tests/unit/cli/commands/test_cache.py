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
    from ratchetr.cli.helpers import CLIContext

pytestmark = [pytest.mark.unit, pytest.mark.cli]


def test_handle_clear_removes_directory(cli_context: CLIContext) -> None:
    # Arrange
    target = cli_context.resolved_paths.cache_dir
    target.mkdir(parents=True, exist_ok=True)
    args = Namespace(cache_action="clear")

    # Act
    exit_code = cache_cmd.execute_cache(args, cli_context)

    # Assert
    assert exit_code == 0
    assert not target.exists()


def test_handle_clear_handles_missing_directory(cli_context: CLIContext) -> None:
    # Arrange
    target = cli_context.resolved_paths.cache_dir
    if target.exists():
        target.rmdir()
    args = Namespace(cache_action="clear")

    # Act
    exit_code = cache_cmd.execute_cache(args, cli_context)

    # Assert
    assert exit_code == 0


def test_execute_cache_unknown_action(cli_context: CLIContext) -> None:
    # Act / Assert
    with pytest.raises(SystemExit, match=r".*"):
        _ = cache_cmd.execute_cache(Namespace(cache_action="invalid"), cli_context)
