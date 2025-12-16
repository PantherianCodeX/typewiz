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

"""Tests for manifest aggregation helpers."""

from __future__ import annotations

from collections import Counter

import pytest

from ratchetr.core.model_types import RecommendationCode, SeverityLevel
from ratchetr.core.type_aliases import RuleName
from ratchetr.manifest.aggregate import (
    FileSummary,
    FolderSummary,
    _canonical_category_mapping,
    _Categoriser,
    _split_rel_path,
    _update_file_summary,
)

pytestmark = pytest.mark.unit


def test_canonical_category_mapping_filters_and_orders() -> None:
    raw = {
        "unknownChecks": ["Foo", "foo", ""],
        "invalid": ["bar"],
    }
    canonical = _canonical_category_mapping(raw)
    assert canonical["unknownChecks"] == ("foo",)
    assert "invalid" not in canonical


def test_folder_summary_recommendations_change_based_on_counts() -> None:
    summary = FolderSummary(path="src", depth=1)
    payload = summary.to_folder_entry()
    assert RecommendationCode.STRICT_READY.value in payload["recommendations"]

    summary.errors = 1
    summary.code_counts["unknown-type"] = 2
    summary.category_counts["unknownChecks"] = 0
    entry = summary.to_folder_entry()
    assert any("unknown-type" in recommendation for recommendation in entry["recommendations"])


def test_categoriser_matches_fallback_and_custom_patterns() -> None:
    categoriser = _Categoriser({"optionalChecks": ["opt"]})
    assert categoriser.categorise("optimize") == "optionalChecks"
    assert categoriser.categorise("unknown-type") == "unknownChecks"


def test_split_rel_path_normalizes_and_caches() -> None:
    path = "src/module/app.py"
    parts = _split_rel_path(path)
    assert parts[0] == "src"
    assert _split_rel_path(path) == parts


def test_update_file_summary_increments_counts() -> None:
    file_summary = FileSummary(path="src/app.py")
    severity_totals = Counter()
    rule_totals: Counter[RuleName] = Counter()
    category_totals = Counter()
    categoriser = _Categoriser({})
    _update_file_summary(
        file_summary,
        severity=SeverityLevel.ERROR,
        code="E",
        diagnostic={
            "line": 1,
            "column": 1,
            "severity": "error",
            "code": "E",
            "message": "msg",
        },
        severity_totals=severity_totals,
        rule_totals=rule_totals,
        category_totals=category_totals,
        categoriser=categoriser,
    )
    assert file_summary.errors == 1
    assert rule_totals[RuleName("E")] == 1
