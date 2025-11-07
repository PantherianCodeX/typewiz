# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

from typing import cast

from typewiz.model_types import ReadinessStatus
from typewiz.readiness import CATEGORY_PATTERNS, ReadinessEntry, ReadinessOptions, compute_readiness
from typewiz.summary_types import ReadinessOptionsBucket
from typewiz.type_aliases import CategoryName


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
    ready_entries = readiness["strict"][ReadinessStatus.READY]
    assert len(ready_entries) == 1
    assert ready_entries[0].get("path") == "src/pkg"
    options = readiness["options"]
    for category in CATEGORY_PATTERNS:
        bucket = options[category]
        ready_bucket = bucket.get(ReadinessStatus.READY.value)
        assert isinstance(ready_bucket, list)
        assert ready_bucket


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
    close_entries = readiness["strict"][ReadinessStatus.CLOSE]
    assert len(close_entries) == 1
    strict_entry = close_entries[0]
    assert strict_entry.get("diagnostics") == 2
    category_status = strict_entry.get("categoryStatus") or {}
    assert category_status.get(CategoryName("unknownChecks")) == ReadinessStatus.CLOSE
    assert strict_entry.get("notes")
    options_bucket = readiness["options"]["unknownChecks"].get(ReadinessStatus.CLOSE.value)
    assert isinstance(options_bucket, list) and options_bucket
    first_folder = options_bucket[0]
    assert first_folder.get("path") == "src/pkg"


def test_compute_readiness_general_extra() -> None:
    entry = cast(
        ReadinessEntry,
        {
            "path": "src/pkg",
            "errors": 2,
            "warnings": 1,
            "information": 0,
            "codeCounts": {},
            "categoryCounts": {"unknownChecks": 1, "custom": 2},
            "recommendations": [],
        },
    )
    readiness = compute_readiness([entry])
    close_entries = readiness["strict"][ReadinessStatus.CLOSE]
    assert close_entries
    categories = close_entries[0].get("categories") or {}
    assert categories.get(CategoryName("general")) == 2
    options_bucket = readiness["options"]["unknownChecks"].get(ReadinessStatus.CLOSE.value)
    assert isinstance(options_bucket, list) and options_bucket
    assert options_bucket[0].get("count") == 1


def test_readiness_options_roundtrip() -> None:
    bucket_payload: ReadinessOptionsBucket = {
        "threshold": 4,
        ReadinessStatus.READY.value: [{"path": "src/pkg", "count": 1}],
        ReadinessStatus.BLOCKED.value: [{"path": "src/blocked", "errors": 2}],
    }
    options = ReadinessOptions.from_payload(bucket_payload, default_threshold=2)
    ready_bucket = options.buckets[ReadinessStatus.READY]
    assert ready_bucket and ready_bucket[0].get("path") == "src/pkg"
    assert options.threshold == 4
    payload = options.to_payload()
    payload_ready = payload.get(ReadinessStatus.READY.value)
    assert isinstance(payload_ready, list) and payload_ready
    assert payload_ready[0].get("path") == "src/pkg"
    payload_blocked = payload.get(ReadinessStatus.BLOCKED.value)
    assert isinstance(payload_blocked, list) and payload_blocked
    assert payload_blocked[0].get("errors") == 2
