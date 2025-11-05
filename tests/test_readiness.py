from __future__ import annotations

from typewiz.readiness import CATEGORY_PATTERNS, ReadinessEntry, compute_readiness


def test_compute_readiness_ready_bucket() -> None:
    entry: ReadinessEntry = {
        "path": "src/pkg",
        "errors": 0,
        "warnings": 0,
        "information": 0,
        "codeCounts": {},
        "categoryCounts": {},
        "recommendations": [],
    }
    readiness = compute_readiness([entry])
    ready_entries = readiness["strict"]["ready"]
    assert len(ready_entries) == 1
    assert ready_entries[0].get("path") == "src/pkg"
    options = readiness["options"]
    for category in CATEGORY_PATTERNS:
        bucket = options[category]
        assert bucket["ready"]


def test_compute_readiness_close_notes() -> None:
    entry: ReadinessEntry = {
        "path": "src/pkg",
        "errors": 1,
        "warnings": 1,
        "information": 0,
        "codeCounts": {"reportUnknownVariableType": 2},
        "categoryCounts": {},
        "recommendations": ["fix unknowns"],
    }
    readiness = compute_readiness([entry])
    close_entries = readiness["strict"]["close"]
    assert len(close_entries) == 1
    strict_entry = close_entries[0]
    assert strict_entry.get("diagnostics") == 2
    category_status = strict_entry.get("categoryStatus") or {}
    assert category_status.get("unknownChecks") == "close"
    assert strict_entry.get("notes")
    options_bucket = readiness["options"]["unknownChecks"]["close"]
    assert options_bucket and options_bucket[0]["path"] == "src/pkg"


def test_compute_readiness_general_extra() -> None:
    entry: ReadinessEntry = {
        "path": "src/pkg",
        "errors": 2,
        "warnings": 1,
        "information": 0,
        "codeCounts": {},
        "categoryCounts": {"unknownChecks": 1, "custom": 2},
        "recommendations": [],
    }
    readiness = compute_readiness([entry])
    close_entries = readiness["strict"]["close"]
    assert close_entries
    categories = close_entries[0].get("categories") or {}
    assert categories.get("general") == 2
    assert readiness["options"]["unknownChecks"]["close"][0]["count"] == 1
