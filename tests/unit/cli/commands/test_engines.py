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

"""Unit tests for the engines CLI command."""

from __future__ import annotations

import argparse

import pytest

from ratchetr.cli.commands import engines as engines_cmd
from ratchetr.cli.helpers.options import StdoutFormat
from ratchetr.engines.registry import EngineDescriptor

pytestmark = [pytest.mark.unit, pytest.mark.cli]


def test_execute_engines_unknown_action() -> None:
    args = argparse.Namespace(engines_action="unknown", out=StdoutFormat.TEXT.value)
    with pytest.raises(SystemExit):
        _ = engines_cmd.execute_engines(args, None)


def test_handle_list_renders_descriptors(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    descriptor = EngineDescriptor(
        name="pyright",
        module="ratchetr.engines.builtin.pyright",
        qualified_name="PyrightEngine",
        origin="builtin",
    )
    monkeypatch.setattr("ratchetr.cli.commands.engines.describe_engines", lambda: [descriptor])

    args = argparse.Namespace(engines_action="list", out=StdoutFormat.JSON.value)
    exit_code = engines_cmd.execute_engines(args, None)

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "pyright" in output
