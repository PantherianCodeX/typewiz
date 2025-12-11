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

"""Fixtures for multi-component integration tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ratchetr.core.model_types import Mode, SeverityLevel
from ratchetr.core.type_aliases import ToolName
from ratchetr.core.types import Diagnostic, RunResult

if TYPE_CHECKING:
    from pathlib import Path

STUB_TOOL = ToolName("stub")


@pytest.fixture
def fake_run(tmp_path: Path) -> RunResult:
    """Provide a representative run payload for CLI->engine workflows.

    Returns:
        `RunResult`with a single diagnostic referencing ``tmp_path``.
    """
    (tmp_path / "pkg").mkdir(exist_ok=True)
    diag = Diagnostic(
        tool=STUB_TOOL,
        severity=SeverityLevel.ERROR,
        path=tmp_path / "pkg" / "module.py",
        line=1,
        column=1,
        code="reportGeneralTypeIssues",
        message="oops",
        raw={},
    )
    return RunResult(
        tool=STUB_TOOL,
        mode=Mode.CURRENT,
        command=["stub"],
        exit_code=1,
        duration_ms=1.0,
        diagnostics=[diag],
    )
