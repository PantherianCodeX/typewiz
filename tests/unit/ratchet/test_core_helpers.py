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

"""Unit tests for helper utilities in ``ratchet.core``."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, cast

import pytest

from ratchetr.core.model_types import DEFAULT_SEVERITIES, Mode, SeverityLevel
from ratchetr.core.type_aliases import RunId
from ratchetr.ratchet import core as ratchet_core
from ratchetr.ratchet.models import RatchetModel, RatchetPathBudgetModel, RatchetRunBudgetModel

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from ratchetr.json import JSONValue
    from ratchetr.manifest.typed import ManifestData

pytestmark = [pytest.mark.unit, pytest.mark.ratchet]


def _map_payload(payload: dict[str, object]) -> Mapping[str, JSONValue]:
    return cast("Mapping[str, JSONValue]", payload)


def _sample_manifest() -> ManifestData:
    return cast(
        "ManifestData",
        {
            "generatedAt": "2025-01-01T00:00:00Z",
            "projectRoot": "/repo",
            "runs": [
                {
                    "tool": "pyright",
                    "mode": "current",
                    "perFile": [],
                    "engineOptions": {},
                }
            ],
        },
    )


def test_normalise_mode_accepts_modes_and_rejects_invalid() -> None:
    assert ratchet_core._normalise_mode(Mode.CURRENT) is Mode.CURRENT
    assert ratchet_core._normalise_mode("target") == Mode.TARGET
    assert ratchet_core._normalise_mode("nope") is None


def test_severity_counts_from_file_prefers_diagnostics_over_totals() -> None:
    entry = _map_payload({
        "diagnostics": [
            {"severity": "warning"},
            {"severity": ""},
            {"severity": "error"},
        ],
        "errors": 5,
        "warnings": 5,
    })
    counts = ratchet_core._severity_counts_from_file(entry)
    assert counts[SeverityLevel.WARNING] == 1
    assert counts[SeverityLevel.ERROR] == 1


def test_severity_counts_from_file_uses_total_fields_when_no_diagnostics() -> None:
    entry = _map_payload({"errors": 2, "warnings": 1, "information": 3})
    counts = ratchet_core._severity_counts_from_file(entry)
    assert counts[SeverityLevel.ERROR] == 2
    assert counts[SeverityLevel.WARNING] == 1
    assert counts[SeverityLevel.INFORMATION] == 3


def test_overrides_and_category_mapping_are_normalised() -> None:
    raw = _map_payload({
        "overrides": [{"b": 2, "a": 1}],
        "categoryMapping": {
            "general": ["src"],
            "invalid": ["skip"],
        },
    })
    overrides = ratchet_core._normalise_overrides(raw)
    assert overrides == [{"a": 1, "b": 2}]
    category_map = ratchet_core._normalise_category_mapping(raw)
    assert category_map == {"general": ["src"]}


def test_canonicalise_engine_options_handles_full_payload_and_none() -> None:
    raw = _map_payload({
        "profile": "baseline",
        "configFile": "pyproject.toml",
        "pluginArgs": ["--strict"],
        "include": ["src"],
        "exclude": ["tests"],
        "overrides": [{"foo": "bar"}],
        "categoryMapping": {"general": ["src"]},
    })
    normalised = ratchet_core._canonicalise_engine_options(raw)
    assert normalised["profile"] == "baseline"
    assert normalised["configFile"] == "pyproject.toml"
    assert normalised["pluginArgs"] == ["--strict"]
    assert normalised["include"] == ["src"]
    assert normalised["exclude"] == ["tests"]
    assert normalised["overrides"] == [{"foo": "bar"}]
    assert normalised["categoryMapping"] == {"general": ["src"]}
    assert ratchet_core._canonicalise_engine_options(None) == {}


def test_normalise_severity_list_handles_empty_and_duplicates() -> None:
    assert ratchet_core._normalise_severity_list(None) == list(DEFAULT_SEVERITIES)
    assert ratchet_core._normalise_severity_list([]) == list(DEFAULT_SEVERITIES)
    filtered = ratchet_core._normalise_severity_list(cast("Sequence[SeverityLevel]", [None, None]))
    assert filtered == list(DEFAULT_SEVERITIES)
    deduped = ratchet_core._normalise_severity_list([SeverityLevel.WARNING, SeverityLevel.WARNING, SeverityLevel.ERROR])
    assert deduped == [SeverityLevel.ERROR, SeverityLevel.WARNING]


def test_split_targets_parses_global_and_scoped_values() -> None:
    global_map, per_run = ratchet_core._split_targets({
        "error": -2,
        "pyright:current.warning": 3,
        "pyright:current.error": 4,
        "": 10,
    })
    assert global_map == {SeverityLevel.ERROR: 0}
    assert per_run["pyright:current"][SeverityLevel.WARNING] == 3
    assert per_run["pyright:current"][SeverityLevel.ERROR] == 4


def test_build_path_budgets_skips_invalid_paths_and_defaults_counts() -> None:
    entries = [
        {"path": "", "errors": 1},
        {
            "path": "src/main.py",
            "diagnostics": [{"severity": "error"}],
        },
    ]
    budgets = ratchet_core._build_path_budgets(entries, [SeverityLevel.ERROR, SeverityLevel.WARNING])
    assert "src/main.py" in budgets
    assert budgets["src/main.py"].severities[SeverityLevel.ERROR] == 1
    assert budgets["src/main.py"].severities[SeverityLevel.WARNING] == 0


def test_engine_signature_payload_and_hash_include_expected_fields() -> None:
    run = _map_payload({
        "tool": "pyright",
        "mode": "current",
        "engineOptions": {"profile": "baseline"},
    })
    payload = ratchet_core._engine_signature_payload(run)
    signature = ratchet_core._signature_payload_with_hash(run)
    assert payload["tool"] == "pyright"
    assert payload["mode"] == Mode.CURRENT
    assert "hash" in signature
    assert ratchet_core._engine_signature_hash(payload) == signature["hash"]


def test_collect_manifest_runs_and_lookup_helpers_ignore_bad_entries() -> None:
    manifest = cast("ManifestData", {"runs": 123})
    assert ratchet_core._collect_manifest_runs(manifest) == []
    manifest = cast(
        "ManifestData",
        {
            "runs": [
                _map_payload({"tool": "pyright", "mode": "current"}),
                _map_payload({"tool": "", "mode": ""}),
            ]
        },
    )
    assert ratchet_core._select_run_ids(manifest, None) == [RunId("pyright:current")]
    assert ratchet_core._select_run_ids(manifest, ["pyright:current"]) == [RunId("pyright:current")]
    lookup = ratchet_core._run_by_id(manifest)
    assert RunId("pyright:current") in lookup
    assert RunId("pyright:target") not in lookup


def test_run_id_helpers_trim_blanks() -> None:
    values = ["pyright:current", RunId("mypy:target"), " "]
    normalised = ratchet_core._normalise_run_id_values(values)
    assert RunId("pyright:current") in normalised
    assert RunId("mypy:target") in normalised
    assert len(normalised) == 2
    assert RunId("pyright:current") in ratchet_core._normalise_run_id_set(values)


def test_collect_path_counts_filters_empty_paths() -> None:
    entries = [
        {"path": "", "errors": 1},
        {"path": "src/app.py", "errors": 2},
    ]
    counts = ratchet_core._collect_path_counts(entries)
    assert "src/app.py" in counts
    assert "" not in counts


def test_updated_path_budgets_uses_targets_and_actual_counts() -> None:
    budget_model = RatchetPathBudgetModel(severities={SeverityLevel.ERROR: 2, SeverityLevel.WARNING: 1})
    run_budget = RatchetRunBudgetModel.model_validate({
        "severities": [SeverityLevel.ERROR.value, SeverityLevel.WARNING.value],
        "paths": {"src/app.py": budget_model},
        "targets": {SeverityLevel.ERROR.value: 1, SeverityLevel.WARNING.value: 0},
    })
    path_counts = {"src/app.py": Counter({SeverityLevel.ERROR: 1, SeverityLevel.WARNING: 3})}
    updated = ratchet_core._updated_path_budgets(run_budget, path_counts)
    assert updated["src/app.py"].severities[SeverityLevel.ERROR] == 1
    assert updated["src/app.py"].severities[SeverityLevel.WARNING] == 1


def test_compare_severity_budget_reports_violation_improvement_and_equal() -> None:
    violation, improvement = ratchet_core._compare_severity_budget(
        path="src/app.py",
        severity=SeverityLevel.ERROR,
        allowed=1,
        actual=2,
    )
    assert violation is not None
    assert improvement is None
    violation, improvement = ratchet_core._compare_severity_budget(
        path="src/app.py",
        severity=SeverityLevel.ERROR,
        allowed=3,
        actual=1,
    )
    assert violation is None
    assert improvement is not None
    violation, improvement = ratchet_core._compare_severity_budget(
        path="src/app.py",
        severity=SeverityLevel.ERROR,
        allowed=1,
        actual=1,
    )
    assert violation is None
    assert improvement is None


def test_evaluate_run_report_records_improvements_when_actual_counts_missing() -> None:
    run_budget = RatchetRunBudgetModel.model_validate({
        "severities": [SeverityLevel.ERROR.value, SeverityLevel.WARNING.value],
        "paths": {
            "src/app.py": {
                "severities": {
                    SeverityLevel.ERROR.value: 2,
                    SeverityLevel.WARNING.value: 1,
                }
            }
        },
        "targets": {
            SeverityLevel.ERROR.value: 1,
            SeverityLevel.WARNING.value: 0,
        },
    })
    manifest_run = _map_payload({
        "tool": "pyright",
        "mode": "current",
        "perFile": [],
        "engineOptions": {},
    })
    report = ratchet_core._evaluate_run_report(RunId("pyright:current"), run_budget, manifest_run)
    assert report.improvements
    assert not report.signature_matches


def test_compare_manifest_to_ratchet_respects_requested_runs() -> None:
    ratchet_model = RatchetModel.model_validate({
        "generatedAt": "2025-02-01T00:00:00Z",
        "manifestPath": None,
        "projectRoot": None,
        "runs": {
            "pyright:current": {"severities": ["error"], "paths": {}},
            "pyright:target": {"severities": ["error"], "paths": {}},
        },
    })
    manifest = _sample_manifest()
    report = ratchet_core.compare_manifest_to_ratchet(
        manifest=manifest,
        ratchet=ratchet_model,
        runs=["pyright:current"],
    )
    assert len(report.runs) == 1
