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

"""Unit tests for Misc Dashboard."""

from __future__ import annotations

import copy
from collections import Counter, defaultdict
from typing import TYPE_CHECKING, cast

import pytest

from ratchetr._infra.utils import consume
from ratchetr.api import build_summary, load_manifest, render_html, render_markdown
from ratchetr.core.model_types import OverrideEntry, SeverityLevel
from ratchetr.core.type_aliases import RelPath, RunId
from ratchetr.dashboard.build import (
    _build_engine_options_payload,
    _consume_run,
    _FolderAccumulators,
    _prepare_run_payload,
    _SummaryState,
)
from ratchetr.dashboard.render_html import (
    READINESS_PREVIEW_LIMIT,
    _as_mapping,
    _coerce_override_list,
    _coerce_str_list,
    _format_code_list,
    _format_override_html,
    _overview_category_section,
    _render_readiness_strict_entries,
)
from ratchetr.manifest.models import ManifestValidationError
from ratchetr.manifest.versioning import CURRENT_MANIFEST_VERSION

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from ratchetr.core.summary_types import SummaryData
    from ratchetr.json import JSONValue
    from ratchetr.manifest.typed import FileEntry, FolderEntry, ManifestData, RunPayload

pytestmark = pytest.mark.unit


def test_render_markdown_snapshot(
    sample_summary: SummaryData,
    snapshot_text: Callable[[str], str],
) -> None:
    output = render_markdown(sample_summary)
    assert output == snapshot_text("dashboard.md")


def test_render_html_snapshot(
    sample_summary: SummaryData,
    snapshot_text: Callable[[str], str],
) -> None:
    output = render_html(sample_summary)
    assert output == snapshot_text("dashboard.html")


def test_render_html_includes_category_table_when_data_present(sample_summary: SummaryData) -> None:
    summary = copy.deepcopy(sample_summary)
    category_totals = {"general": 2}
    summary["categoryTotals"] = category_totals
    summary["tabs"]["overview"]["categoryTotals"] = category_totals
    html = render_html(summary)
    assert "<th>Category</th>" in html
    assert "general" in html


def test_render_html_reports_no_rule_paths_when_entries_missing(sample_summary: SummaryData) -> None:
    summary = copy.deepcopy(sample_summary)
    summary["ruleFiles"] = {"missing": []}
    summary["tabs"]["hotspots"]["ruleFiles"] = {"missing": []}
    html = render_html(summary)
    assert "No matching paths" in html


def test_render_html_reports_no_rule_breakdown_when_empty() -> None:
    manifest = {
        "generatedAt": "now",
        "projectRoot": ".",
        "schemaVersion": CURRENT_MANIFEST_VERSION,
        "runs": [],
    }
    summary = build_summary(manifest)
    summary["ruleFiles"] = {}
    summary["tabs"]["hotspots"]["ruleFiles"] = {}
    html = render_html(summary)
    assert "No rule hotspot breakdown available." in html


def test_render_html_records_no_runs_for_empty_summary() -> None:
    manifest = {
        "generatedAt": "now",
        "projectRoot": ".",
        "schemaVersion": CURRENT_MANIFEST_VERSION,
        "runs": [],
    }
    summary = build_summary(manifest)
    html = render_html(summary)
    assert "No runs recorded." in html


def test_render_html_handles_empty_engine_options(sample_summary: SummaryData) -> None:
    summary = copy.deepcopy(sample_summary)
    for entry in summary["tabs"]["engines"]["runSummary"].values():
        entry["engineOptions"] = {}
    html = render_html(summary)
    assert "Include paths: —" in html


def test_overview_category_section_handles_empty_mapping() -> None:
    lines = _overview_category_section({}, str)
    assert "No categories recorded" in "\n".join(lines)


def test_format_code_list_returns_expected_variants() -> None:
    assert _format_code_list([], str) == "—"
    assert "<code>" in _format_code_list(["only"], str)
    assert ", " in _format_code_list(["one", "two"], str)


def test_format_override_html_highlights_details() -> None:
    override: OverrideEntry = {
        "path": "src/app.py",
        "profile": "strict",
        "pluginArgs": ["--foo"],
        "include": [RelPath("src")],
        "exclude": [RelPath("tests")],
    }
    html = _format_override_html(override, str)
    assert "plugin args" in html
    assert "include" in html
    assert "exclude" in html


def test_format_override_html_falls_back_to_profile() -> None:
    override: OverrideEntry = {"path": "src/app.py", "profile": "strict"}
    html = _format_override_html(override, str)
    assert "profile=" in html


def test_coerce_str_list_and_overrides_and_mapping_helpers() -> None:
    assert _coerce_str_list("value") == []
    assert _coerce_str_list(["a", 1]) == ["a", "1"]
    assert _coerce_override_list(["nope", {"path": "src"}]) == [{"path": "src"}]
    assert _as_mapping({"foo": "bar"}) == {"foo": "bar"}
    assert _as_mapping("not") == {}


def test_render_readiness_strict_entries_handles_empty_and_overflow() -> None:
    empty_lines = _render_readiness_strict_entries(str, [], "Label")
    assert "Label" in "\n".join(empty_lines)
    entries = [
        {"path": f"src/file{i}.py", "diagnostics": i, "notes": [str(i)]} for i in range(READINESS_PREVIEW_LIMIT + 2)
    ]
    lines = _render_readiness_strict_entries(str, entries, "Label")
    assert "plus" in "\n".join(lines)


def test_build_summary_minimal(tmp_path: Path) -> None:
    manifest: ManifestData = {
        "projectRoot": str(tmp_path),
        "generatedAt": "now",
        "schemaVersion": CURRENT_MANIFEST_VERSION,
        "runs": [],
    }
    summary = build_summary(manifest)
    assert summary["runSummary"] == {}
    assert summary["tabs"]["overview"]["severityTotals"] == {}


def test_load_manifest_reads_file(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    consume(
        manifest_path.write_text(
            f'{{"schemaVersion": "{CURRENT_MANIFEST_VERSION}", "runs": []}}',
            encoding="utf-8",
        ),
    )
    data = load_manifest(manifest_path)
    assert "runs" in data
    assert data["runs"] == []


def test_load_manifest_discards_invalid_runs(tmp_path: Path) -> None:
    manifest_path = tmp_path / "manifest.json"
    consume(
        manifest_path.write_text(
            f'{{"schemaVersion": "{CURRENT_MANIFEST_VERSION}", "runs": ["not-a-run", 3]}}',
            encoding="utf-8",
        ),
    )
    with pytest.raises(ManifestValidationError, match="Input should be a valid dictionary"):
        _ = load_manifest(manifest_path)


def test_build_summary_skips_missing_entries(tmp_path: Path) -> None:
    manifest: ManifestData = {
        "projectRoot": str(tmp_path),
        "generatedAt": "now",
        "schemaVersion": CURRENT_MANIFEST_VERSION,
        "runs": [
            cast(
                "RunPayload",
                {
                    "tool": "stub",
                    "mode": "target",
                    "command": [],
                    "exitCode": 0,
                    "durationMs": 1,
                    "summary": {
                        "severityBreakdown": {},
                        "ruleCounts": {},
                        "categoryCounts": {},
                    },
                    "engineOptions": {},
                    "perFolder": cast(
                        "list[FolderEntry]",
                        [{"path": None, "errors": 1, "warnings": 1}],
                    ),
                    "perFile": cast(
                        "list[FileEntry]",
                        [{"path": "pkg/module.py", "errors": 0, "warnings": 0}],
                    ),
                },
            ),
        ],
    }
    summary = build_summary(manifest)
    assert summary["topFolders"] == []
    assert summary["topFiles"] == []


def test_render_markdown_handles_empty_runs() -> None:
    manifest: ManifestData = {
        "generatedAt": "now",
        "projectRoot": ".",
        "schemaVersion": CURRENT_MANIFEST_VERSION,
        "runs": [],
    }
    summary = build_summary(manifest)
    output = render_markdown(summary)
    assert "_No runs recorded_" in output
    assert "No engine data" in output


def test_render_markdown_tool_totals_mismatch(sample_summary: SummaryData) -> None:
    summary = copy.deepcopy(sample_summary)
    run_summary = summary["tabs"]["overview"]["runSummary"]
    run_id = RunId("mypy:target")
    assert run_id in run_summary
    target = run_summary[run_id]
    target["toolSummary"] = {"errors": 2, "warnings": 0, "information": 0, "total": 2}
    output = render_markdown(summary)
    assert "mismatch vs parsed" in output


def test_prepare_run_payload_returns_expected_values() -> None:
    run_payload: dict[str, JSONValue] = {
        "tool": "pyright",
        "mode": "current",
        "command": ["pyright"],
        "summary": {"errors": 1, "warnings": 0, "information": 0, "total": 1},
        "engineOptions": {},
    }
    payload = _prepare_run_payload(run_payload)
    assert payload is not None
    run_id, summary_map, options_map, command = payload
    assert str(run_id) == "pyright:current"
    assert summary_map["errors"] == 1
    assert options_map == {}
    assert command == ["pyright"]


def test_build_engine_options_payload_normalizes_lists() -> None:
    payload = _build_engine_options_payload(
        cast(
            "dict[str, JSONValue]",
            {
                "profile": "baseline",
                "configFile": "pyrightconfig.json",
                "pluginArgs": ["--strict"],
                "include": ["src"],
                "exclude": ["tests"],
                "overrides": [
                    {
                        "path": "src/app.py",
                        "pluginArgs": ["--strict"],
                        "include": ["src"],
                        "exclude": [],
                    },
                ],
                "categoryMapping": {"unknownChecks": ["reportMissingType"]},
            },
        )
    )
    assert payload.get("pluginArgs") == ["--strict"]
    assert payload.get("include") == [RelPath("src")]
    category_mapping = payload.get("categoryMapping") or {}
    assert category_mapping.get("unknownChecks") == ["reportMissingType"]


def test_consume_run_updates_summary_state() -> None:
    run_payload: dict[str, JSONValue] = {
        "tool": "pyright",
        "mode": "current",
        "command": ["pyright"],
        "summary": {
            "errors": 1,
            "warnings": 0,
            "information": 0,
            "total": 1,
            "severityBreakdown": {"error": 1},
            "ruleCounts": {"TEST": 1},
            "categoryCounts": {"unknownChecks": 1},
        },
        "engineOptions": {},
        "perFolder": [
            {
                "path": "src",
                "errors": 1,
                "warnings": 0,
                "information": 0,
                "codeCounts": {},
                "categoryCounts": {},
            },
        ],
        "perFile": [
            {
                "path": "src/app.py",
                "errors": 1,
                "warnings": 0,
                "information": 0,
                "diagnostics": [{"code": "TEST"}],
            }
        ],
    }
    state = _SummaryState(
        run_summary={},
        severity_totals=Counter(),
        rule_totals=Counter(),
        category_totals=Counter(),
        folder_stats=_FolderAccumulators(
            totals=defaultdict(Counter),
            counts=defaultdict(int),
            code_totals=defaultdict(Counter),
            category_totals=defaultdict(Counter),
            recommendations=defaultdict(set),
        ),
        file_entries=[],
        rule_file_counts=defaultdict(Counter),
    )
    _consume_run(run_payload, state=state)
    assert RunId("pyright:current") in state.run_summary
    assert state.severity_totals[SeverityLevel.ERROR] == 1
    assert state.folder_stats.totals["src"]["errors"] == 1
    assert state.rule_file_counts["TEST"]["src/app.py"] == 1
