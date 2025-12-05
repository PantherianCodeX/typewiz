# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Unit tests for Readiness."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pytest

from typewiz.core.model_types import ReadinessStatus
from typewiz.core.type_aliases import CategoryName
from typewiz.readiness.compute import (
    CATEGORY_PATTERNS,
    ReadinessEntry,
    ReadinessOptions,
    compute_readiness,
)

if TYPE_CHECKING:
    from typewiz.core.summary_types import ReadinessOptionsPayload

pytestmark = pytest.mark.unit


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
        buckets_map = bucket.get("buckets")
        assert isinstance(buckets_map, dict)
        ready_bucket = buckets_map.get(ReadinessStatus.READY)
        assert isinstance(ready_bucket, tuple)
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
    strict_close_entries = readiness["strict"][ReadinessStatus.CLOSE]
    assert len(strict_close_entries) == 1
    strict_entry = strict_close_entries[0]
    assert strict_entry.get("diagnostics") == 2
    category_status = strict_entry.get("categoryStatus") or {}
    assert category_status.get(CategoryName("unknownChecks")) == ReadinessStatus.CLOSE
    assert strict_entry.get("notes")
    options_bucket = readiness["options"]["unknownChecks"].get("buckets")
    assert isinstance(options_bucket, dict)
    close_option_entries = options_bucket.get(ReadinessStatus.CLOSE)
    assert isinstance(close_option_entries, tuple)
    assert close_option_entries
    first_folder = close_option_entries[0]
    assert first_folder.get("path") == "src/pkg"


def test_compute_readiness_general_extra() -> None:
    entry = cast(
        "ReadinessEntry",
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
    strict_close_entries = readiness["strict"][ReadinessStatus.CLOSE]
    assert strict_close_entries
    categories = strict_close_entries[0].get("categories") or {}
    assert categories.get(CategoryName("general")) == 2
    options_bucket = readiness["options"]["unknownChecks"].get("buckets")
    assert isinstance(options_bucket, dict)
    close_option_entries = options_bucket.get(ReadinessStatus.CLOSE)
    assert isinstance(close_option_entries, tuple)
    assert close_option_entries
    assert close_option_entries[0].get("count") == 1


def test_readiness_options_roundtrip() -> None:
    bucket_payload: ReadinessOptionsPayload = {
        "threshold": 4,
        "buckets": {
            ReadinessStatus.READY: ({"path": "src/pkg", "count": 1},),
            ReadinessStatus.BLOCKED: ({"path": "src/blocked", "errors": 2},),
        },
    }
    options = ReadinessOptions.from_payload(bucket_payload, default_threshold=2)
    ready_bucket = options.buckets[ReadinessStatus.READY]
    assert ready_bucket
    assert ready_bucket[0].get("path") == "src/pkg"
    assert options.threshold == 4
    payload = options.to_payload()
    buckets = payload.get("buckets")
    assert isinstance(buckets, dict)
    payload_ready = buckets.get(ReadinessStatus.READY)
    assert isinstance(payload_ready, tuple)
    assert payload_ready
    assert payload_ready[0].get("path") == "src/pkg"
    payload_blocked = buckets.get(ReadinessStatus.BLOCKED)
    assert isinstance(payload_blocked, tuple)
    assert payload_blocked
    assert payload_blocked[0].get("errors") == 2
