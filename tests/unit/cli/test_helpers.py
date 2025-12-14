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

"""Unit tests for CLI helper utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pytest

from ratchetr.cli.helpers import (
    collect_profile_args,
    parse_comma_separated,
    parse_hash_workers,
    parse_int_mapping,
    parse_key_value_entries,
    print_summary,
    render_data,
)
from ratchetr.cli.helpers.formatting import (
    FolderHotspotEntry,
    query_engines,
    query_hotspots,
    query_overview,
    query_readiness,
    query_rules,
    query_runs,
)
from ratchetr.core.model_types import (
    DataFormat,
    HotspotKind,
    ReadinessLevel,
    ReadinessStatus,
    SummaryField,
    SummaryStyle,
)

if TYPE_CHECKING:
    from ratchetr.core.summary_types import SummaryData
    from ratchetr.core.types import RunResult
    from ratchetr.readiness.views import FolderReadinessPayload

pytestmark = [pytest.mark.unit, pytest.mark.cli]


def test_parse_comma_separated_strips_entries() -> None:
    assert parse_comma_separated("foo, bar ,,,baz") == ["foo", "bar", "baz"]
    assert parse_comma_separated(None) == []


def test_parse_key_value_entries_returns_pairs() -> None:
    pairs = parse_key_value_entries(["runner=strict", "mypy = baseline"], argument="--profile")
    assert pairs == [("runner", "strict"), ("mypy", "baseline")]


def test_parse_key_value_entries_rejects_invalid() -> None:
    with pytest.raises(SystemExit, match=r".*"):
        _ = parse_key_value_entries(["novalue"], argument="--profile")


def test_parse_int_mapping_converts_to_ints() -> None:
    mapping = parse_int_mapping(["errors=1", "warnings=0"], argument="--target")
    assert mapping == {"errors": 1, "warnings": 0}


def test_parse_int_mapping_rejects_non_int() -> None:
    with pytest.raises(SystemExit, match=r".*"):
        _ = parse_int_mapping(["errors=abc"], argument="--target")


def test_collect_profile_args_uses_helper() -> None:
    result = collect_profile_args(["pyright=baseline"])
    assert result == {"pyright": "baseline"}


def test_parse_hash_workers_accepts_values() -> None:
    assert parse_hash_workers("4") == 4
    assert parse_hash_workers("auto") == "auto"
    assert parse_hash_workers(None) is None


def test_parse_hash_workers_rejects_invalid() -> None:
    with pytest.raises(SystemExit, match=r".*"):
        _ = parse_hash_workers("-1")
    with pytest.raises(SystemExit, match=r".*"):
        _ = parse_hash_workers("fast")


def test_render_data_accepts_enum() -> None:
    rows = render_data({"key": "value"}, DataFormat.TABLE)
    assert rows[0].startswith("key")


def test_query_overview_payload_shapes(cli_summary: SummaryData) -> None:
    payload = query_overview(cli_summary, include_categories=True, include_runs=True)
    assert payload["severity_totals"]["error"] == 2
    assert payload.get("category_totals", {})["unknownChecks"] == 2
    runs = payload.get("runs")
    assert runs
    assert runs[0]["run"] == "pyright:current"


def test_query_hotspots_file_payload(cli_summary: SummaryData) -> None:
    entries = query_hotspots(cli_summary, kind=HotspotKind.FILES, limit=1)
    assert entries[0]["path"] == "src/app.py"
    folders = cast("list[FolderHotspotEntry]", query_hotspots(cli_summary, kind=HotspotKind.FOLDERS, limit=1))
    assert folders[0]["participating_runs"] == 1


def test_query_runs_and_engines_payloads(cli_summary: SummaryData) -> None:
    runs = query_runs(cli_summary, tools=["pyright"], modes=["current"], limit=5)
    assert runs[0]["command"] == "pyright --strict"
    engines = query_engines(cli_summary, limit=5)
    assert engines[0]["plugin_args"] == ["--strict"]


def test_query_rules_default_paths(cli_summary: SummaryData) -> None:
    entries = query_rules(cli_summary, limit=1, default_paths=True)
    paths = entries[0].get("paths")
    assert paths is not None
    assert paths[0]["path"] == "src/app.py"


def test_query_readiness_payload(cli_summary: SummaryData) -> None:
    view = cast(
        "dict[ReadinessStatus, list[FolderReadinessPayload]]",
        query_readiness(
            cli_summary,
            level=ReadinessLevel.FOLDER,
            statuses=[ReadinessStatus.BLOCKED],
            limit=5,
        ),
    )
    assert ReadinessStatus.BLOCKED in view
    assert view[ReadinessStatus.BLOCKED][0]["path"] == "src"


def test_format_run_header_includes_counts(
    cli_run_result: RunResult,
    capsys: pytest.CaptureFixture[str],
) -> None:
    print_summary([cli_run_result], fields=[], style=SummaryStyle.COMPACT)
    header = capsys.readouterr().out.strip().splitlines()[0]
    assert "pyright:current" in header
    assert "errors=1" in header


def test_profile_and_path_details_respect_expanded_flag(
    cli_run_result: RunResult,
    capsys: pytest.CaptureFixture[str],
) -> None:
    print_summary(
        [cli_run_result],
        fields=[SummaryField.PROFILE, SummaryField.PATHS],
        style=SummaryStyle.EXPANDED,
    )
    output = capsys.readouterr().out.splitlines()
    assert any("profile: strict" in line for line in output)
    assert any("include: src" in line for line in output)
    assert any("exclude: tests" in line for line in output)
