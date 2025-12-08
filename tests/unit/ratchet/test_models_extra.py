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

"""Additional unit tests for ratchet models."""

from __future__ import annotations

import pytest

from ratchetr.core.model_types import SeverityLevel
from ratchetr.core.type_aliases import RunId
from ratchetr.ratchet.models import (
    RatchetModel,
    RatchetPathBudgetModel,
    RatchetRunBudgetModel,
)


def test_path_budget_requires_mapping() -> None:
    with pytest.raises(TypeError, match="severities must be a mapping"):
        RatchetPathBudgetModel.model_validate({"severities": 1})


def test_run_budget_severities_requires_sequence() -> None:
    with pytest.raises(TypeError, match="severities must be a string or sequence"):
        RatchetRunBudgetModel.model_validate({"severities": 1})


def test_run_budget_targets_requires_mapping() -> None:
    with pytest.raises(TypeError, match="targets must be a mapping"):
        RatchetRunBudgetModel.model_validate({
            "severities": ["error"],
            "targets": 1,
        })


def test_run_budget_normalises_values() -> None:
    run_model = RatchetRunBudgetModel.model_validate({
        "severities": ["warning", "error", "warning"],
        "paths": {
            "src/app.py": {
                "severities": {SeverityLevel.ERROR: 1},
            },
        },
        "targets": {SeverityLevel.WARNING: 2},
    })
    assert run_model.severities == [SeverityLevel.ERROR, SeverityLevel.WARNING]
    assert isinstance(run_model.paths["src/app.py"], RatchetPathBudgetModel)
    assert run_model.targets[SeverityLevel.WARNING] == 2


def test_ratchet_model_normalises_run_keys() -> None:
    raw_runs: dict[str, object] = {
        "b:current": {
            "severities": ["error"],
            "paths": {},
            "targets": {},
        },
        "a:full": {
            "severities": ["warning"],
            "paths": {},
            "targets": {},
        },
    }
    model = RatchetModel.model_validate({
        "generatedAt": "2025-01-01T00:00:00Z",
        "manifestPath": None,
        "projectRoot": None,
        "runs": raw_runs,
    })
    assert list(model.runs.keys()) == [RunId("a:full"), RunId("b:current")]
