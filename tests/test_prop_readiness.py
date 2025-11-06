# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

import hypothesis.strategies as st
from hypothesis import given

from typewiz.model_types import ReadinessStatus
from typewiz.readiness_views import collect_readiness_view
from typewiz.summary_types import (
    ReadinessOptionEntry,
    ReadinessOptionsBucket,
    ReadinessStrictEntry,
    ReadinessTab,
    SummaryData,
    SummaryTabs,
)

STATUS_VALUES = tuple(status.value for status in ReadinessStatus)


def _status() -> st.SearchStrategy[str]:
    return st.sampled_from(STATUS_VALUES)


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
    bucket = st.builds(
        ReadinessOptionsBucket,
        ready=st.lists(_folder_entry(), max_size=3),
        close=st.lists(_folder_entry(), max_size=3),
        blocked=st.lists(_folder_entry(), max_size=3),
        threshold=st.integers(min_value=0, max_value=10),
    )
    strict_map: st.SearchStrategy[dict[str, list[ReadinessStrictEntry]]] = st.fixed_dictionaries(
        {status: st.lists(_strict_entry(), max_size=3) for status in STATUS_VALUES},
    )
    options_map: st.SearchStrategy[dict[str, ReadinessOptionsBucket]] = st.fixed_dictionaries(
        {
            "unknownChecks": bucket,
            "optionalChecks": bucket,
            "unusedSymbols": bucket,
            "general": bucket,
        },
    )

    def _build_tab(
        strict: dict[str, list[ReadinessStrictEntry]],
        options: dict[str, ReadinessOptionsBucket],
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
    statuses: list[str],
    limit: int,
) -> None:
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

    # Folder view
    folder_view = collect_readiness_view(summary, level="folder", statuses=statuses, limit=limit)
    for stat, entries in folder_view.items():
        assert stat in STATUS_VALUES
        assert isinstance(entries, list)
        if limit > 0:
            assert len(entries) <= limit
        for e in entries:
            assert isinstance(e.get("path"), str)
            assert isinstance(e.get("count"), int)
            assert isinstance(e.get("errors"), int)
            assert isinstance(e.get("warnings"), int)

    # File view
    file_view = collect_readiness_view(summary, level="file", statuses=statuses, limit=limit)
    for stat, entries in file_view.items():
        assert stat in STATUS_VALUES
        if limit > 0:
            assert len(entries) <= limit
        for e in entries:
            assert isinstance(e.get("path"), str)
            assert isinstance(e.get("diagnostics"), int)
            assert isinstance(e.get("errors"), int)
            assert isinstance(e.get("warnings"), int)
            assert isinstance(e.get("information"), int)
