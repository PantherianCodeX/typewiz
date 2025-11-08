# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

from typing import cast

import hypothesis.strategies as st
from hypothesis import given

from typewiz.core.model_types import ReadinessLevel, ReadinessStatus
from typewiz.core.summary_types import (
    ReadinessOptionEntry,
    ReadinessOptionsPayload,
    ReadinessStrictEntry,
    ReadinessTab,
    SummaryData,
    SummaryTabs,
)
from typewiz.core.type_aliases import CategoryKey
from typewiz.readiness.views import (
    FileReadinessPayload,
    FolderReadinessPayload,
    collect_readiness_view,
)


def _status() -> st.SearchStrategy[ReadinessStatus]:
    return st.sampled_from(tuple(ReadinessStatus))


def _folder_entry() -> st.SearchStrategy[ReadinessOptionEntry]:
    return st.builds(
        ReadinessOptionEntry,
        path=st.text(min_size=1, max_size=20),
        count=st.integers(min_value=0, max_value=50),
        errors=st.integers(min_value=0, max_value=50),
        warnings=st.integers(min_value=0, max_value=50),
    )


def _strict_entry() -> st.SearchStrategy[ReadinessStrictEntry]:
    return st.builds(
        ReadinessStrictEntry,
        path=st.text(min_size=1, max_size=20),
        diagnostics=st.integers(min_value=0, max_value=100),
        errors=st.integers(min_value=0, max_value=100),
        warnings=st.integers(min_value=0, max_value=100),
        information=st.integers(min_value=0, max_value=100),
    )


def _readiness_tab() -> st.SearchStrategy[ReadinessTab]:
    def _build_bucket(
        ready_entries: list[ReadinessOptionEntry],
        close_entries: list[ReadinessOptionEntry],
        blocked_entries: list[ReadinessOptionEntry],
        threshold: int,
    ) -> ReadinessOptionsPayload:
        buckets: dict[ReadinessStatus, tuple[ReadinessOptionEntry, ...]] = {}
        if ready_entries:
            buckets[ReadinessStatus.READY] = tuple(ready_entries)
        if close_entries:
            buckets[ReadinessStatus.CLOSE] = tuple(close_entries)
        if blocked_entries:
            buckets[ReadinessStatus.BLOCKED] = tuple(blocked_entries)
        return {"threshold": threshold, "buckets": buckets}

    bucket = st.builds(
        _build_bucket,
        st.lists(_folder_entry(), max_size=3),
        st.lists(_folder_entry(), max_size=3),
        st.lists(_folder_entry(), max_size=3),
        st.integers(min_value=0, max_value=10),
    )

    def _build_strict_map(
        ready_entries: list[ReadinessStrictEntry],
        close_entries: list[ReadinessStrictEntry],
        blocked_entries: list[ReadinessStrictEntry],
    ) -> dict[ReadinessStatus, list[ReadinessStrictEntry]]:
        return {
            ReadinessStatus.READY: ready_entries,
            ReadinessStatus.CLOSE: close_entries,
            ReadinessStatus.BLOCKED: blocked_entries,
        }

    strict_map: st.SearchStrategy[dict[ReadinessStatus, list[ReadinessStrictEntry]]] = st.builds(
        _build_strict_map,
        st.lists(_strict_entry(), max_size=3),
        st.lists(_strict_entry(), max_size=3),
        st.lists(_strict_entry(), max_size=3),
    )

    def _build_options_map(
        unknown: ReadinessOptionsPayload,
        optional: ReadinessOptionsPayload,
        unused: ReadinessOptionsPayload,
        general: ReadinessOptionsPayload,
    ) -> dict[CategoryKey, ReadinessOptionsPayload]:
        return {
            "unknownChecks": unknown,
            "optionalChecks": optional,
            "unusedSymbols": unused,
            "general": general,
        }

    options_map: st.SearchStrategy[dict[CategoryKey, ReadinessOptionsPayload]] = st.builds(
        _build_options_map,
        bucket,
        bucket,
        bucket,
        bucket,
    )

    def _build_tab(
        strict: dict[ReadinessStatus, list[ReadinessStrictEntry]],
        options: dict[CategoryKey, ReadinessOptionsPayload],
    ) -> ReadinessTab:
        return {"strict": strict, "options": options}

    return st.builds(_build_tab, strict_map, options_map)


@given(
    _readiness_tab(),
    st.lists(_status(), unique=True, max_size=3),
    st.integers(min_value=0, max_value=5),
)
def test_h_collect_readiness_view_shapes(
    readiness_tab: ReadinessTab,
    statuses: list[ReadinessStatus],
    limit: int,
) -> None:
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
        "topFiles": [],
        "ruleFiles": {},
        "tabs": tabs,
    }

    # Folder view
    folder_view: dict[ReadinessStatus, list[FolderReadinessPayload]] = cast(
        dict[ReadinessStatus, list[FolderReadinessPayload]],
        collect_readiness_view(
            summary,
            level=ReadinessLevel.FOLDER,
            statuses=statuses,
            limit=limit,
        ),
    )
    for stat, folder_entries in folder_view.items():
        assert isinstance(stat, ReadinessStatus)
        assert isinstance(folder_entries, list)
        if limit > 0:
            assert len(folder_entries) <= limit
        for folder_entry in folder_entries:
            assert isinstance(folder_entry["path"], str)
            assert isinstance(folder_entry["count"], int)
            assert isinstance(folder_entry["errors"], int)
            assert isinstance(folder_entry["warnings"], int)

    # File view
    file_view: dict[ReadinessStatus, list[FileReadinessPayload]] = cast(
        dict[ReadinessStatus, list[FileReadinessPayload]],
        collect_readiness_view(
            summary,
            level=ReadinessLevel.FILE,
            statuses=statuses,
            limit=limit,
        ),
    )
    for stat, file_entries in file_view.items():
        assert isinstance(stat, ReadinessStatus)
        if limit > 0:
            assert len(file_entries) <= limit
        for file_entry in file_entries:
            assert isinstance(file_entry["path"], str)
            assert isinstance(file_entry["diagnostics"], int)
            assert isinstance(file_entry["errors"], int)
            assert isinstance(file_entry["warnings"], int)
            assert isinstance(file_entry["information"], int)
