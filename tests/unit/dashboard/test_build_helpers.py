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

"""Tests for Dashboard summary builder helpers."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import TYPE_CHECKING, cast

import pytest

from ratchetr.core.model_types import ReadinessStatus, SeverityLevel
from ratchetr.dashboard import build as dashboard_build
from ratchetr.dashboard.build import DashboardTypeError

if TYPE_CHECKING:
    from ratchetr.json import JSONValue
    from ratchetr.manifest.typed import ManifestData


pytestmark = pytest.mark.unit


def _minimal_run(tool: str = "pyright") -> dict[str, object]:
    return {
        "tool": tool,
        "mode": "current",
        "summary": {
            "errors": 1,
            "warnings": 2,
            "information": 0,
            "total": 3,
            "severityBreakdown": {"error": 1},
            "ruleCounts": {"E1": 1},
            "categoryCounts": {"unknownChecks": 1},
        },
        "perFolder": [
            {
                "path": "src",
                "errors": 1,
                "warnings": 0,
                "information": 0,
                "codeCounts": {"E1": 1},
                "categoryCounts": {"general": 1},
                "recommendations": ["fix"],
            },
        ],
        "perFile": [
            {"path": "src/app.py", "errors": 1, "warnings": 0, "information": 0, "diagnostics": [{"code": "E1"}]},
        ],
        "engineOptions": {"profile": "baseline"},
    }


def _manifest_builder() -> dict[str, object]:
    return {
        "projectRoot": ".",
        "generatedAt": "now",
        "runs": [_minimal_run()],
    }


def _new_summary_state() -> dashboard_build._SummaryState:
    return dashboard_build._SummaryState(
        run_summary={},
        severity_totals=Counter(),
        rule_totals=Counter(),
        category_totals=Counter(),
        folder_stats=dashboard_build._FolderAccumulators(
            totals=defaultdict(Counter),
            counts=defaultdict(int),
            code_totals=defaultdict(Counter),
            category_totals=defaultdict(Counter),
            recommendations=defaultdict(set),
        ),
        file_entries=[],
        rule_file_counts=defaultdict(Counter),
    )


def test_coerce_status_key_rejects_unknown_status() -> None:
    with pytest.raises(DashboardTypeError, match=r"readiness\.strict"):
        _ = dashboard_build._coerce_status_key("unknown")


def test_require_category_key_rejects_invalid() -> None:
    with pytest.raises(DashboardTypeError, match=r"readiness\.options"):
        _ = dashboard_build._require_category_key("bad", "readiness.options")


def test_coerce_readiness_entries_demands_sequence() -> None:
    with pytest.raises(DashboardTypeError, match=r"readiness\.strict"):
        _ = dashboard_build._coerce_readiness_entries("not-a-sequence", "readiness.strict.ready")


def test_build_readiness_options_raises_for_invalid_bucket() -> None:
    mapping: dict[str, JSONValue] = {
        "general": {
            "threshold": "bad",
            "buckets": {},
        }
    }
    with pytest.raises(DashboardTypeError, match="threshold"):
        _ = dashboard_build._build_readiness_options(mapping)


def test_build_summary_populates_hotspots_and_tabs() -> None:
    manifest = cast("ManifestData", _manifest_builder())
    summary = dashboard_build.build_summary(manifest)
    assert summary["topRules"]
    assert summary["tabs"]["overview"]["severityTotals"][SeverityLevel.ERROR] == 1
    assert summary["tabs"]["hotspots"]["topFolders"][0]["path"] == "src"
    hotspots = summary["tabs"]["hotspots"]
    assert hotspots["ruleFiles"]["E1"]


def test_maybe_severity_level_handles_known_values() -> None:
    assert dashboard_build._maybe_severity_level("error") == SeverityLevel.ERROR
    assert dashboard_build._maybe_severity_level("invalid") is None


def test_coerce_readiness_entries_accepts_sequences() -> None:
    entries = dashboard_build._coerce_readiness_entries(
        [{"path": "src", "diagnostics": 1}],
        "readiness.strict",
    )
    assert entries == [{"path": "src", "diagnostics": 1}]


def test_build_readiness_options_parses_payload() -> None:
    options_map = {
        "general": {
            "threshold": 5,
            "buckets": {
                "ready": [
                    {
                        "path": "src",
                        "diagnostics": 2,
                        "notes": ["keep it clean"],
                    },
                ],
                "close": [],
                "blocked": [],
            },
        },
    }
    result = dashboard_build._build_readiness_options(options_map)
    payload = result["general"]
    assert payload["threshold"] == 5
    assert ReadinessStatus.READY in payload["buckets"]


def test_validate_readiness_tab_requires_mappings() -> None:
    with pytest.raises(DashboardTypeError, match=r"readiness\.strict"):
        dashboard_build._validate_readiness_tab({"strict": "bad", "options": {}})
    with pytest.raises(DashboardTypeError, match=r"readiness\.options"):
        dashboard_build._validate_readiness_tab({"strict": {"ready": []}, "options": "bad"})


def test_validate_readiness_tab_returns_structured_payload() -> None:
    raw = {
        "strict": {
            "ready": [{"path": "src", "diagnostics": 0}],
        },
        "options": {
            "general": {
                "threshold": 3,
                "buckets": {
                    "ready": [],
                    "close": [],
                    "blocked": [],
                },
            },
        },
    }
    validated = dashboard_build._validate_readiness_tab(raw)
    assert ReadinessStatus.READY in validated["strict"]
    assert "general" in validated["options"]


def test_build_readiness_section_logs_invalid_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    def _explode(_: object) -> object:
        msg = "boom"
        raise ValueError(msg)

    monkeypatch.setattr(dashboard_build, "_validate_readiness_tab", _explode)
    result = dashboard_build._build_readiness_section([])
    assert result["strict"][ReadinessStatus.READY] == []
    assert result["options"] == {}


def test_coerce_status_key_accepts_enum_and_rejects_other_types() -> None:
    status = ReadinessStatus.CLOSE
    assert dashboard_build._coerce_status_key(status) is status
    with pytest.raises(DashboardTypeError, match=r"readiness\.strict"):
        _ = dashboard_build._coerce_status_key(123)


def test_maybe_severity_level_handles_enum_and_non_strings() -> None:
    assert dashboard_build._maybe_severity_level(SeverityLevel.WARNING) == SeverityLevel.WARNING
    assert dashboard_build._maybe_severity_level(0) is None


def test_coerce_readiness_entries_handles_none_and_invalid_items() -> None:
    assert dashboard_build._coerce_readiness_entries(None, "context") == []
    with pytest.raises(DashboardTypeError, match=r"context\[0\]"):
        _ = dashboard_build._coerce_readiness_entries([1], "context")


def test_coerce_run_entries_ignores_non_sequence() -> None:
    manifest = cast("ManifestData", {"runs": "not-a-list"})
    assert dashboard_build._coerce_run_entries(manifest) == []


def test_prepare_run_payload_returns_none_when_missing_values() -> None:
    payload = {"mode": "current", "summary": {"errors": 0}}
    assert dashboard_build._prepare_run_payload(payload) is None


def test_parse_manifest_overrides_filters_invalid_entries() -> None:
    overrides = dashboard_build._parse_manifest_overrides([
        {"path": "src", "profile": "baseline", "pluginArgs": ["--strict"], "include": ["src"], "exclude": ["tests"]},
        "invalid",
    ])
    assert overrides
    assert overrides[0]["path"] == "src"


def test_parse_category_mapping_filters_invalid_keys_and_cleans_values() -> None:
    mapping = {
        "unknown": ["val"],
        "general": ["valid", "", "  extra  "],
    }
    assert dashboard_build._parse_category_mapping(mapping) == {"general": ["valid", "extra"]}


def test_parse_severity_breakdown_ignores_unknown_levels() -> None:
    summary = {"severityBreakdown": {"error": 1, "not-a-level": 2}}
    breakdown = dashboard_build._parse_severity_breakdown(summary)
    assert SeverityLevel.ERROR in breakdown
    assert len(breakdown) == 1


def test_update_folder_metrics_consumes_entries_and_recommendations() -> None:
    folder_stats = _new_summary_state().folder_stats
    entries = [
        {
            "path": "src",
            "errors": 1,
            "warnings": 1,
            "information": 0,
            "codeCounts": {"E1": 1},
            "categoryCounts": {"invalid": 1},
            "recommendations": ["  fix ", None, ""],
        },
    ]
    dashboard_build._update_folder_metrics(entries, folder_stats)
    assert folder_stats.totals["src"]["errors"] == 1
    assert not folder_stats.category_totals["src"]
    assert "fix" in folder_stats.recommendations["src"]


def test_update_file_metrics_skips_zero_counters_and_handles_diagnostics() -> None:
    file_entries: list[tuple[str, int, int, int]] = []
    rule_counts: dict[str, Counter[str]] = defaultdict(Counter)
    entries = [
        {"path": "src/app.py", "errors": 0, "warnings": 0, "information": 0},
        {
            "path": "src/app.py",
            "errors": 1,
            "warnings": 0,
            "information": 0,
            "diagnostics": ["not a mapping", {"code": "E1"}],
        },
    ]
    dashboard_build._update_file_metrics(entries, file_entries, rule_counts)
    assert file_entries
    assert rule_counts["E1"]["src/app.py"] == 1


def test_consume_run_ignores_incomplete_payload() -> None:
    state = _new_summary_state()
    incomplete = {"tool": "pyright"}  # missing mode and summary
    dashboard_build._consume_run(incomplete, state=state)
    assert not state.run_summary


def test_build_readiness_options_rejects_non_mappings() -> None:
    with pytest.raises(DashboardTypeError, match=r"readiness\.options"):
        _ = dashboard_build._build_readiness_options({"general": "bad"})
    with pytest.raises(DashboardTypeError, match=r"buckets"):
        _ = dashboard_build._build_readiness_options({"general": {"buckets": "bad"}})
