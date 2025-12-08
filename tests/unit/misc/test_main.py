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

"""Unit tests for Misc Main."""

from __future__ import annotations

import runpy

import pytest

pytestmark = pytest.mark.unit


def test_main_module_invokes_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, object] = {}

    def fake_main() -> int:
        called["hit"] = True
        return 5

    monkeypatch.setattr("ratchetr.cli.main", fake_main)
    with pytest.raises(SystemExit, match=r".*") as excinfo:
        _ = runpy.run_module("ratchetr.__main__", run_name="__main__")
    assert excinfo.value.code == 5
    assert called["hit"] is True
