# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Tests for readiness view helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.fixtures.builders import build_readiness_summary
from typewiz.core.categories import CategoryName
from typewiz.core.model_types import ReadinessLevel, ReadinessStatus, SeverityLevel
from typewiz.readiness.compute import DEFAULT_CLOSE_THRESHOLD, ReadinessOptions
from typewiz.readiness.views import (
    ReadinessValidationError,
    _build_option_entry,
    _build_strict_entry,
    _coerce_option_entries,
    _coerce_options_bucket,
    _coerce_options_map,
    _coerce_status,
    _coerce_strict_entries,
    _coerce_strict_map,
    _extract_file_entries,
    _file_matches_severity,
    _file_payload_for_status,
    _folder_matches_severity,
    _folder_payload_for_status,
    _normalise_file_entry,
    _normalise_severity_filters,
    _normalise_status_filters,
    collect_readiness_view,
)

if TYPE_CHECKING:
    from typewiz.core.summary_types import SummaryData


def test_coerce_status_handles_invalid_values() -> None:
    assert _coerce_status("invalid") == ReadinessStatus.BLOCKED
    assert _coerce_status(ReadinessStatus.READY) == ReadinessStatus.READY


def test_build_option_entry_and_entries_helper() -> None:
    entry = {"path": "src", "count": 1, "errors": 0, "warnings": 2}
    built = _build_option_entry(entry)
    assert built["path"] == "src"
    entries = _coerce_option_entries([entry, "ignore"])
    assert entries
    assert entries[0]["path"] == "src"


def test_build_strict_entry_appends_notes() -> None:
    entry = {
        "path": "src/app.py",
        "diagnostics": 2,
        "notes": ["a"],
        "recommendations": ["b"],
        "categoryStatus": {"unknownChecks": "blocked"},
    }
    strict = _build_strict_entry(entry)
    assert strict["notes"] == ["a"]
    assert strict["recommendations"] == ["b"]


def test_coerce_options_bucket_and_map_ignores_bad_buckets() -> None:
    bucket = {
        "threshold": 4,
        "buckets": {
            "ready": [{"path": "src", "diagnostics": 1}],
            "invalid": {"bogus": True},
        },
    }
    result = _coerce_options_bucket(bucket)
    assert result.threshold == 4
    assert ReadinessStatus.READY in result.buckets
    options = _coerce_options_map({"unknownChecks": bucket, "bad": "skip"})
    assert "unknownChecks" in options


def test_build_strict_entry_records_categories() -> None:
    entry = {
        "path": "src/app.py",
        "diagnostics": 2,
        "notes": ["a"],
        "recommendations": ["b"],
        "categories": {"unknownChecks": 1},
        "categoryStatus": {"unknownChecks": "blocked"},
    }
    strict = _build_strict_entry(entry)
    assert CategoryName("unknownChecks") in strict["categories"]


def test_coerce_options_bucket_handles_non_mapping() -> None:
    bucket = _coerce_options_bucket("invalid")
    assert bucket.threshold == DEFAULT_CLOSE_THRESHOLD


def test_coerce_options_map_skips_invalid_categories() -> None:
    options = _coerce_options_map({"invalid": {}, "general": {"threshold": 1, "buckets": {}}})
    assert "general" in options


def test_coerce_strict_map_with_entries() -> None:
    strict_map = {"ready": [{"path": "src"}]}
    result = _coerce_strict_map(strict_map)
    assert ReadinessStatus.READY in result


def test_normalise_file_entry_rejects_negative_counts() -> None:
    entry = {"path": "src", "diagnostics": -1, "errors": 0, "warnings": 0, "information": 0}
    with pytest.raises(ValueError, match="diagnostics must be non-negative"):
        _normalise_file_entry(entry)
    entry["diagnostics"] = 1
    entry["errors"] = -1
    with pytest.raises(ValueError, match="errors must be non-negative"):
        _normalise_file_entry(entry)
    entry["errors"] = 0
    entry["warnings"] = -1
    with pytest.raises(ValueError, match="warnings must be non-negative"):
        _normalise_file_entry(entry)
    entry["warnings"] = 0
    entry["information"] = -1
    with pytest.raises(ValueError, match="information must be non-negative"):
        _normalise_file_entry(entry)


def test_normalise_filters_and_matches() -> None:
    assert _normalise_status_filters(None) == [ReadinessStatus.BLOCKED]
    assert _normalise_status_filters([ReadinessStatus.READY, ReadinessStatus.READY]) == [ReadinessStatus.READY]
    assert _normalise_severity_filters([SeverityLevel.ERROR, SeverityLevel.ERROR]) == (SeverityLevel.ERROR,)
    record = type("Record", (), {"errors": 1, "warnings": 0, "information": 0})()
    assert _folder_matches_severity(record, [SeverityLevel.ERROR])
    assert _file_matches_severity(record, [SeverityLevel.ERROR]) is True


def test_folder_and_file_payloads_include_records() -> None:
    options = ReadinessOptions(threshold=1)
    options.add_entry(ReadinessStatus.BLOCKED, {"path": "src", "count": 1, "errors": 1, "warnings": 0})
    payload = _folder_payload_for_status(
        {"general": options}, ReadinessStatus.BLOCKED, limit=1, severities=[SeverityLevel.ERROR]
    )
    assert payload

    strict_entry = {"path": "src/app.py", "diagnostics": 1, "errors": 1, "warnings": 0, "information": 0}
    file_payload = _file_payload_for_status(
        {ReadinessStatus.BLOCKED: [strict_entry]}, ReadinessStatus.BLOCKED, limit=1, severities=[SeverityLevel.ERROR]
    )
    assert file_payload


def test_extract_file_entries_handles_missing_status() -> None:
    entries = _extract_file_entries({ReadinessStatus.READY: []}, ReadinessStatus.BLOCKED)
    assert entries == []


def test_coerce_strict_map_and_entries_skip_invalid() -> None:
    strict_map = {"ready": [{"path": "src"}], None: None}
    coerced = _coerce_strict_map(strict_map)
    assert ReadinessStatus.READY in coerced
    assert _coerce_strict_entries("not-a-sequence") == []
    assert _coerce_strict_entries([{"path": "src"}])


def test_collect_readiness_view_folder_limits_and_defaults() -> None:
    summary: SummaryData = build_readiness_summary(
        option_entries={
            ReadinessStatus.BLOCKED: [
                {"path": "src/app", "count": 4, "errors": 1, "warnings": 1},
                {"path": "src/other", "count": 5, "errors": 2, "warnings": 1},
            ],
        },
        strict_entries={
            ReadinessStatus.BLOCKED: [
                {"path": "src/app.py", "diagnostics": 3, "errors": 2, "warnings": 1, "information": 0},
            ],
        },
    )
    view = collect_readiness_view(summary, level=ReadinessLevel.FOLDER, statuses=None, limit=1)
    blocked_entries = view[ReadinessStatus.BLOCKED]
    assert len(blocked_entries) == 1
    assert blocked_entries[0]["path"] == "src/app"


def test_collect_readiness_view_folder_severity_filter_removes_information() -> None:
    summary: SummaryData = build_readiness_summary(
        option_entries={
            ReadinessStatus.BLOCKED: [
                {"path": "src/app", "count": 2, "errors": 1, "warnings": 1},
            ],
        },
    )
    filtered = collect_readiness_view(
        summary,
        level=ReadinessLevel.FOLDER,
        statuses=[ReadinessStatus.BLOCKED],
        limit=0,
        severities=[SeverityLevel.INFORMATION],
    )
    assert filtered[ReadinessStatus.BLOCKED] == []


def test_collect_readiness_view_file_defaults_and_severity_filter() -> None:
    summary: SummaryData = build_readiness_summary(
        strict_entries={
            ReadinessStatus.BLOCKED: [
                {"path": "src/app.py", "diagnostics": 2, "errors": 1, "warnings": 1, "information": 0},
            ],
        },
    )
    view = collect_readiness_view(summary, level=ReadinessLevel.FILE, statuses=None, limit=1)
    file_entries = view[ReadinessStatus.BLOCKED]
    assert file_entries
    assert file_entries[0]["path"] == "src/app.py"

    filtered = collect_readiness_view(
        summary,
        level=ReadinessLevel.FILE,
        statuses=[ReadinessStatus.BLOCKED],
        limit=1,
        severities=[SeverityLevel.INFORMATION],
    )
    assert filtered[ReadinessStatus.BLOCKED] == []


def test_collect_readiness_view_file_validation_error_propagates() -> None:
    summary: SummaryData = build_readiness_summary(
        strict_entries={
            ReadinessStatus.BLOCKED: [
                {"path": "src/app.py", "diagnostics": 2, "errors": 1, "warnings": 1, "information": 0},
            ],
        },
    )
    strict_map = summary["tabs"]["readiness"]["strict"]
    blocked_entries = strict_map[ReadinessStatus.BLOCKED]
    blocked_entries[0]["diagnostics"] = -1

    with pytest.raises(ReadinessValidationError, match="diagnostics must be non-negative"):
        collect_readiness_view(
            summary,
            level=ReadinessLevel.FILE,
            statuses=[ReadinessStatus.BLOCKED],
            limit=1,
        )
