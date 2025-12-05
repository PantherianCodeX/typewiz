# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Tests for readiness compute helpers."""

from __future__ import annotations

from typewiz.core.model_types import ReadinessStatus
from typewiz.core.type_aliases import CategoryName
from typewiz.readiness.compute import (
    CATEGORY_CLOSE_THRESHOLD,
    ReadinessEntry,
    ReadinessOptions,
    _bucket_code_counts,
    _category_counts_from_entry,
    _status_for_category,
)


def test_readiness_options_from_payload_handles_varied_entries() -> None:
    payload = {
        "threshold": 5,
        "buckets": {
            "ready": [{"path": "src", "diagnostics": 1}],
            "close": ({"path": "lib", "diagnostics": 2},),
            "invalid": [{"path": "bad"}],
            123: [{"path": "skip"}],
        },
    }
    options = ReadinessOptions.from_payload(payload)
    assert options.threshold == 5
    assert ReadinessStatus.READY in options.buckets
    assert tuple(entry["path"] for entry in options.buckets[ReadinessStatus.READY]) == ("src",)


def test_category_counts_from_entry_ignores_invalid_values() -> None:
    entry: ReadinessEntry = {
        "path": "src",
        "errors": 1,
        "warnings": 0,
        "information": 0,
        "codeCounts": {},
        "categoryCounts": {"general": 2, "unknown": "bad"},
        "recommendations": [],
    }
    categories = _category_counts_from_entry(entry)
    assert categories[CategoryName("general")] == 2
    assert categories[CategoryName("unknownChecks")] >= 0


def test_bucket_code_counts_applies_fallback() -> None:
    counts = {"UnknownType": 2, "optional-check": 1, "other": 3}
    buckets = _bucket_code_counts(counts)
    assert buckets[CategoryName("unknownChecks")] >= 2
    assert buckets[CategoryName("optionalChecks")] >= 1
    assert buckets[CategoryName("general")] >= 3


def test_status_for_category_respects_thresholds() -> None:
    assert _status_for_category("unknownChecks", 0) is ReadinessStatus.READY
    assert _status_for_category("unknownChecks", 1) is ReadinessStatus.CLOSE
    assert (
        _status_for_category("unknownChecks", CATEGORY_CLOSE_THRESHOLD["unknownChecks"] + 1) is ReadinessStatus.BLOCKED
    )
