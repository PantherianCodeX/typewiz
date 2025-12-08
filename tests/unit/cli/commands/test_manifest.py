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

"""Unit tests covering the manifest CLI command wiring."""

from __future__ import annotations

from argparse import Namespace
from typing import TYPE_CHECKING

import pytest

from ratchetr.cli.commands import manifest as manifest_cmd

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = [pytest.mark.unit, pytest.mark.cli]


def test_handle_schema_writes_requested_path(tmp_path: Path) -> None:
    # Arrange
    output = tmp_path / "schema.json"
    args = Namespace(indent=2, output=output, action="schema")

    # Act
    exit_code = manifest_cmd.execute_manifest(args)

    # Assert
    assert exit_code == 0
    assert output.exists()
    content = output.read_text(encoding="utf-8")
    assert content.startswith("{")
    assert content.rstrip().endswith("}")
