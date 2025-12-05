# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Additional unit tests for ratchet models."""

from __future__ import annotations

import pytest

from typewiz.core.model_types import SeverityLevel
from typewiz.core.type_aliases import RunId
from typewiz.ratchet.models import (
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
