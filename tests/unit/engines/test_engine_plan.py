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

"""Tests for EnginePlan equivalence and canonicalization."""

from pathlib import Path

import pytest

from ratchetr.core.model_types import Mode
from ratchetr.core.type_aliases import ToolName
from ratchetr.engines.base import EnginePlan


def test_engine_plan_equivalence_identical() -> None:
    """Identical plans should be equivalent."""
    plan1 = EnginePlan(
        engine_name=ToolName("mypy"),
        mode=Mode.CURRENT,
        resolved_scope=("src/", "tests/"),
        plugin_args=("--strict",),
        profile="standard",
        config_file=None,
        include=(),
        exclude=(),
        overrides=(),
        category_mapping={},
        root=Path("/project"),
    )
    plan2 = EnginePlan(
        engine_name=ToolName("mypy"),
        mode=Mode.TARGET,  # Different mode
        resolved_scope=("src/", "tests/"),
        plugin_args=("--strict",),
        profile="standard",
        config_file=None,
        include=(),
        exclude=(),
        overrides=(),
        category_mapping={},
        root=Path("/project"),
    )
    assert plan1.is_equivalent_to(plan2)


def test_engine_plan_equivalence_different_scope() -> None:
    """Different scope should not be equivalent."""
    plan1 = EnginePlan(
        engine_name=ToolName("mypy"),
        mode=Mode.CURRENT,
        resolved_scope=("src/",),
        plugin_args=(),
        profile=None,
        config_file=None,
        include=(),
        exclude=(),
        overrides=(),
        category_mapping={},
        root=Path("/project"),
    )
    plan2 = EnginePlan(
        engine_name=ToolName("mypy"),
        mode=Mode.TARGET,
        resolved_scope=("tests/",),
        plugin_args=(),
        profile=None,
        config_file=None,
        include=(),
        exclude=(),
        overrides=(),
        category_mapping={},
        root=Path("/project"),
    )
    assert not plan1.is_equivalent_to(plan2)


def test_engine_plan_equivalence_different_args() -> None:
    """Different plugin args should not be equivalent."""
    plan1 = EnginePlan(
        engine_name=ToolName("mypy"),
        mode=Mode.CURRENT,
        resolved_scope=("src/",),
        plugin_args=("--strict",),
        profile=None,
        config_file=None,
        include=(),
        exclude=(),
        overrides=(),
        category_mapping={},
        root=Path("/project"),
    )
    plan2 = EnginePlan(
        engine_name=ToolName("mypy"),
        mode=Mode.TARGET,
        resolved_scope=("src/",),
        plugin_args=("--no-strict",),
        profile=None,
        config_file=None,
        include=(),
        exclude=(),
        overrides=(),
        category_mapping={},
        root=Path("/project"),
    )
    assert not plan1.is_equivalent_to(plan2)


def test_engine_plan_equivalence_different_config() -> None:
    """Different config file should not be equivalent."""
    plan1 = EnginePlan(
        engine_name=ToolName("mypy"),
        mode=Mode.CURRENT,
        resolved_scope=("src/",),
        plugin_args=(),
        profile=None,
        config_file=Path("/project/mypy.ini"),
        include=(),
        exclude=(),
        overrides=(),
        category_mapping={},
        root=Path("/project"),
    )
    plan2 = EnginePlan(
        engine_name=ToolName("mypy"),
        mode=Mode.TARGET,
        resolved_scope=("src/",),
        plugin_args=(),
        profile=None,
        config_file=None,
        include=(),
        exclude=(),
        overrides=(),
        category_mapping={},
        root=Path("/project"),
    )
    assert not plan1.is_equivalent_to(plan2)


def test_engine_plan_equivalence_different_engine() -> None:
    """Different engine name should not be equivalent."""
    plan1 = EnginePlan(
        engine_name=ToolName("mypy"),
        mode=Mode.CURRENT,
        resolved_scope=("src/",),
        plugin_args=(),
        profile=None,
        config_file=None,
        include=(),
        exclude=(),
        overrides=(),
        category_mapping={},
        root=Path("/project"),
    )
    plan2 = EnginePlan(
        engine_name=ToolName("pyright"),
        mode=Mode.TARGET,
        resolved_scope=("src/",),
        plugin_args=(),
        profile=None,
        config_file=None,
        include=(),
        exclude=(),
        overrides=(),
        category_mapping={},
        root=Path("/project"),
    )
    assert not plan1.is_equivalent_to(plan2)


def test_engine_plan_frozen() -> None:
    """EnginePlan should be immutable."""
    plan = EnginePlan(
        engine_name=ToolName("mypy"),
        mode=Mode.CURRENT,
        resolved_scope=(),
        plugin_args=(),
        profile=None,
        config_file=None,
        include=(),
        exclude=(),
        overrides=(),
        category_mapping={},
        root=Path("/project"),
    )
    with pytest.raises(AttributeError):
        # ignore JUSTIFIED: testing immutability requires assignment attempt
        plan.resolved_scope = ("new/",)  # type: ignore[misc]
