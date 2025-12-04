# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Unit tests for Readiness Views."""

from __future__ import annotations

from typing import cast

import pytest

from typewiz._internal.utils import consume
from typewiz.core.model_types import ReadinessLevel, ReadinessStatus, SeverityLevel
from typewiz.core.summary_types import (
    ReadinessOptionEntry,
    ReadinessOptionsPayload,
    ReadinessStrictEntry,
    ReadinessTab,
    SummaryData,
    SummaryTabs,
)
from typewiz.core.type_aliases import CategoryName
from typewiz.readiness.views import (
    FileReadinessPayload,
    FileReadinessRecord,
    FolderReadinessPayload,
    FolderReadinessRecord,
    ReadinessValidationError,
    collect_readiness_view,
)

pytestmark = pytest.mark.unit


def _make_summary() -> SummaryData:
    strict_blocked: list[ReadinessStrictEntry] = [
        {
            "path": "src/app",
            "diagnostics": 4,
            "errors": 3,
            "warnings": 1,
            "information": 0,
            "categories": {
                CategoryName("unknownChecks"): 3,
                CategoryName("general"): 1,
            },
            "categoryStatus": {
                CategoryName("unknownChecks"): ReadinessStatus.BLOCKED,
                CategoryName("general"): ReadinessStatus.CLOSE,
            },
        },
    ]
    strict_ready: list[ReadinessStrictEntry] = []
    strict_close: list[ReadinessStrictEntry] = []
    readiness_tab: ReadinessTab = {
        "strict": {
            ReadinessStatus.BLOCKED: strict_blocked,
            ReadinessStatus.READY: strict_ready,
            ReadinessStatus.CLOSE: strict_close,
        },
        "options": {
            "unknownChecks": ReadinessOptionsPayload(
                threshold=2,
                buckets={
                    ReadinessStatus.BLOCKED: (
                        ReadinessOptionEntry(path="src/app", count=3, errors=2, warnings=1),
                    ),
                },
            ),
        },
    }
    tabs: SummaryTabs = {
        "overview": {"severityTotals": {}, "categoryTotals": {}, "runSummary": {}},
        "engines": {"runSummary": {}},
        "hotspots": {"topRules": {}, "topFolders": [], "topFiles": [], "ruleFiles": {}},
        "readiness": readiness_tab,
        "runs": {"runSummary": {}},
    }
    summary: SummaryData = {
        "generatedAt": "now",
        "projectRoot": ".",
        "runSummary": {},
        "severityTotals": {},
        "categoryTotals": {},
        "topRules": {},
        "ruleFiles": {},
        "topFolders": [],
        "topFiles": [],
        "tabs": tabs,
    }
    return summary


def test_collect_readiness_view_folder() -> None:
    summary = _make_summary()
    view = collect_readiness_view(
        summary,
        level=ReadinessLevel.FOLDER,
        statuses=[ReadinessStatus.BLOCKED],
        limit=5,
    )
    folder_view = cast(dict[ReadinessStatus, list[FolderReadinessPayload]], view)
    assert ReadinessStatus.BLOCKED in folder_view
    blocked_entries = folder_view[ReadinessStatus.BLOCKED]
    assert blocked_entries
    first_entry = blocked_entries[0]
    assert first_entry["path"] == "src/app"
    assert first_entry["count"] == 3
    assert first_entry["information"] == 0


def test_collect_readiness_view_folder_severity_filter() -> None:
    summary = _make_summary()
    view = collect_readiness_view(
        summary,
        level=ReadinessLevel.FOLDER,
        statuses=[ReadinessStatus.BLOCKED],
        limit=5,
        severities=[SeverityLevel.INFORMATION],
    )
    folder_view = cast(dict[ReadinessStatus, list[FolderReadinessPayload]], view)
    assert folder_view[ReadinessStatus.BLOCKED] == []


def test_collect_readiness_view_file() -> None:
    summary = _make_summary()
    view = collect_readiness_view(
        summary,
        level=ReadinessLevel.FILE,
        statuses=[ReadinessStatus.BLOCKED],
        limit=5,
    )
    file_view = cast(dict[ReadinessStatus, list[FileReadinessPayload]], view)
    assert ReadinessStatus.BLOCKED in file_view
    blocked_entries = file_view[ReadinessStatus.BLOCKED]
    assert blocked_entries
    entry = blocked_entries[0]
    assert entry["path"] == "src/app"
    assert entry["diagnostics"] == 4
    categories = entry.get("categories")
    assert isinstance(categories, dict)
    categories_dict = cast(dict[CategoryName, object], categories)
    assert categories_dict.get(CategoryName("unknownChecks")) == 3


def test_collect_readiness_view_file_severity_filter() -> None:
    summary = _make_summary()
    view = collect_readiness_view(
        summary,
        level=ReadinessLevel.FILE,
        statuses=[ReadinessStatus.BLOCKED],
        limit=5,
        severities=[SeverityLevel.WARNING],
    )
    file_view = cast(dict[ReadinessStatus, list[FileReadinessPayload]], view)
    assert file_view[ReadinessStatus.BLOCKED]
    filtered = collect_readiness_view(
        summary,
        level=ReadinessLevel.FILE,
        statuses=[ReadinessStatus.BLOCKED],
        limit=5,
        severities=[SeverityLevel.INFORMATION],
    )
    filtered_view = cast(dict[ReadinessStatus, list[FileReadinessPayload]], filtered)
    assert filtered_view[ReadinessStatus.BLOCKED] == []


def test_collect_readiness_view_folder_fallback_category() -> None:
    # unknownChecks bucket intentionally empty; optionalChecks contains entries
    readiness_tab: ReadinessTab = {
        "strict": {
            ReadinessStatus.BLOCKED: [],
            ReadinessStatus.READY: [],
            ReadinessStatus.CLOSE: [],
        },
        "options": {
            "unknownChecks": ReadinessOptionsPayload(threshold=2, buckets={}),
            "optionalChecks": ReadinessOptionsPayload(
                threshold=2,
                buckets={
                    ReadinessStatus.BLOCKED: (
                        ReadinessOptionEntry(path="src/opt", count=2, errors=1, warnings=1),
                    ),
                },
            ),
        },
    }
    tabs: SummaryTabs = {
        "overview": {"severityTotals": {}, "categoryTotals": {}, "runSummary": {}},
        "engines": {"runSummary": {}},
        "hotspots": {"topRules": {}, "topFolders": [], "topFiles": [], "ruleFiles": {}},
        "readiness": readiness_tab,
        "runs": {"runSummary": {}},
    }
    summary: SummaryData = {
        "generatedAt": "now",
        "projectRoot": ".",
        "runSummary": {},
        "severityTotals": {},
        "categoryTotals": {},
        "topRules": {},
        "topFolders": [],
        "ruleFiles": {},
        "topFiles": [],
        "tabs": tabs,
    }
    view = collect_readiness_view(
        summary,
        level=ReadinessLevel.FOLDER,
        statuses=[ReadinessStatus.BLOCKED],
        limit=5,
    )
    folder_view = cast(dict[ReadinessStatus, list[FolderReadinessPayload]], view)
    assert folder_view[ReadinessStatus.BLOCKED][0]["path"] == "src/opt"


def test_collect_readiness_view_rejects_invalid() -> None:
    summary = _make_summary()
    # Inject a negative value to trigger validation error
    readiness = summary["tabs"]["readiness"]
    assert "strict" in readiness
    strict_map = readiness["strict"]
    blocked_key = ReadinessStatus.BLOCKED
    assert blocked_key in strict_map
    blocked_entries = strict_map[blocked_key]
    assert blocked_entries
    blocked_entries[0]["diagnostics"] = -1
    with pytest.raises(ReadinessValidationError):
        consume(
            collect_readiness_view(
                summary,
                level=ReadinessLevel.FILE,
                statuses=[ReadinessStatus.BLOCKED],
                limit=5,
            ),
        )


def test_folder_record_to_payload_roundtrip() -> None:
    record = FolderReadinessRecord(path="pkg", count=2, errors=1, warnings=1, information=0)
    payload = record.to_payload()
    assert payload["path"] == "pkg"
    assert payload["errors"] == 1
    assert payload["warnings"] == 1


def test_file_record_to_payload_roundtrip() -> None:
    record = FileReadinessRecord(
        path="pkg",
        diagnostics=3,
        errors=2,
        warnings=1,
        information=0,
        notes=("note",),
        recommendations=("action",),
        categories={CategoryName("unknown"): 2},
        category_status={CategoryName("unknown"): ReadinessStatus.BLOCKED},
    )
    payload = record.to_payload()
    assert payload["path"] == "pkg"
    assert payload.get("notes") == ["note"]
    categories_payload = payload.get("categories")
    assert categories_payload is not None
    assert isinstance(categories_payload, dict)
    assert categories_payload[CategoryName("unknown")] == 2
