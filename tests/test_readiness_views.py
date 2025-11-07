# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

from typing import cast

import pytest

from typewiz.model_types import ReadinessLevel, ReadinessStatus
from typewiz.readiness_views import (
    FileReadinessPayload,
    FileReadinessRecord,
    FolderReadinessPayload,
    FolderReadinessRecord,
    ReadinessValidationError,
    collect_readiness_view,
)
from typewiz.summary_types import (
    ReadinessOptionEntry,
    ReadinessOptionsBucket,
    ReadinessStrictEntry,
    ReadinessTab,
    StatusKey,
    SummaryData,
    SummaryTabs,
)
from typewiz.utils import consume

READY = ReadinessStatus.READY.value
CLOSE = ReadinessStatus.CLOSE.value
BLOCKED = ReadinessStatus.BLOCKED.value


def _make_summary() -> SummaryData:
    strict_blocked: list[ReadinessStrictEntry] = [
        {
            "path": "src/app",
            "diagnostics": 4,
            "errors": 3,
            "warnings": 1,
            "information": 0,
            "categories": {"unknownChecks": 3, "general": 1},
            "categoryStatus": {
                "unknownChecks": ReadinessStatus.BLOCKED,
                "general": ReadinessStatus.CLOSE,
            },
        },
    ]
    strict_ready: list[ReadinessStrictEntry] = []
    strict_close: list[ReadinessStrictEntry] = []
    readiness_ready_options: list[ReadinessOptionEntry] = []
    readiness_close_options: list[ReadinessOptionEntry] = []
    readiness_tab: ReadinessTab = {
        "strict": {
            cast(StatusKey, BLOCKED): strict_blocked,
            cast(StatusKey, READY): strict_ready,
            cast(StatusKey, CLOSE): strict_close,
        },
        "options": {
            "unknownChecks": ReadinessOptionsBucket(
                blocked=[ReadinessOptionEntry(path="src/app", count=3, errors=2, warnings=1)],
                ready=readiness_ready_options,
                close=readiness_close_options,
                threshold=2,
            ),
        },
    }
    tabs: SummaryTabs = {
        "overview": {"severityTotals": {}, "categoryTotals": {}, "runSummary": {}},
        "engines": {"runSummary": {}},
        "hotspots": {"topRules": {}, "topFolders": [], "topFiles": []},
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
    folder_view = cast(dict[str, list[FolderReadinessPayload]], view)
    assert BLOCKED in folder_view
    blocked_entries = folder_view[BLOCKED]
    assert blocked_entries
    first_entry = blocked_entries[0]
    assert first_entry["path"] == "src/app"
    assert first_entry["count"] == 3


def test_collect_readiness_view_file() -> None:
    summary = _make_summary()
    view = collect_readiness_view(
        summary,
        level=ReadinessLevel.FILE,
        statuses=[ReadinessStatus.BLOCKED],
        limit=5,
    )
    file_view = cast(dict[str, list[FileReadinessPayload]], view)
    assert BLOCKED in file_view
    blocked_entries = file_view[BLOCKED]
    assert blocked_entries
    entry = blocked_entries[0]
    assert entry["path"] == "src/app"
    assert entry["diagnostics"] == 4
    categories = entry.get("categories")
    assert isinstance(categories, dict)
    categories_dict = cast(dict[str, object], categories)
    assert categories_dict.get("unknownChecks") == 3


def test_collect_readiness_view_folder_fallback_category() -> None:
    # unknownChecks bucket intentionally empty; optionalChecks contains entries
    readiness_tab: ReadinessTab = {
        "strict": {
            cast(StatusKey, BLOCKED): [],
            cast(StatusKey, READY): [],
            cast(StatusKey, CLOSE): [],
        },
        "options": {
            "unknownChecks": ReadinessOptionsBucket(blocked=[], ready=[], close=[], threshold=2),
            "optionalChecks": ReadinessOptionsBucket(
                blocked=[ReadinessOptionEntry(path="src/opt", count=2, errors=1, warnings=1)],
                ready=[],
                close=[],
                threshold=2,
            ),
        },
    }
    tabs: SummaryTabs = {
        "overview": {"severityTotals": {}, "categoryTotals": {}, "runSummary": {}},
        "engines": {"runSummary": {}},
        "hotspots": {"topRules": {}, "topFolders": [], "topFiles": []},
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
        "topFiles": [],
        "tabs": tabs,
    }
    view = collect_readiness_view(
        summary,
        level=ReadinessLevel.FOLDER,
        statuses=[ReadinessStatus.BLOCKED],
        limit=5,
    )
    folder_view = cast(dict[str, list[FolderReadinessPayload]], view)
    assert folder_view[BLOCKED][0]["path"] == "src/opt"


def test_collect_readiness_view_rejects_invalid() -> None:
    summary = _make_summary()
    # Inject a negative value to trigger validation error
    readiness = summary["tabs"]["readiness"]
    assert "strict" in readiness
    strict_map = readiness["strict"]
    blocked_key = cast(StatusKey, BLOCKED)
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
    record = FolderReadinessRecord(path="pkg", count=2, errors=1, warnings=1)
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
        categories={"unknown": 2},
        category_status={"unknown": ReadinessStatus.BLOCKED},
    )
    payload = record.to_payload()
    assert payload["path"] == "pkg"
    assert payload.get("notes") == ["note"]
    categories_payload = payload.get("categories")
    assert isinstance(categories_payload, dict)
    assert categories_payload["unknown"] == 2
