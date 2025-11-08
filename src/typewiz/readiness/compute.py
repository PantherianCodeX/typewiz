# Copyright (c) 2024 PantherianCodeX. All Rights Reserved.

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final, TypedDict, cast

from typewiz.core.categories import CATEGORY_NAMES
from typewiz.core.model_types import ReadinessStatus
from typewiz.core.summary_types import (
    ReadinessOptionEntry,
    ReadinessOptionsPayload,
    ReadinessStrictEntry,
)
from typewiz.core.type_aliases import CategoryKey, CategoryName

DEFAULT_CLOSE_THRESHOLD: Final[int] = 3
STRICT_CLOSE_THRESHOLD: Final[int] = 3
GENERAL_CATEGORY: Final[CategoryName] = CategoryName("general")
# Category patterns and thresholds can be tuned here without touching renderers
CATEGORY_PATTERNS: Final[dict[CategoryKey, tuple[str, ...]]] = {
    "unknownChecks": (
        "unknown",
        "missingtype",
        "reportunknown",
        "reportmissingtype",
        "untyped",
    ),
    "optionalChecks": ("optional", "nonecheck", "maybeunbound"),
    "unusedSymbols": ("unused", "warnunused", "redundant"),
    "general": (),
}

CATEGORY_CLOSE_THRESHOLD: Final[dict[CategoryKey, int]] = {
    "unknownChecks": 2,
    "optionalChecks": 2,
    "unusedSymbols": 4,
    "general": 5,
}

CATEGORY_LABELS: Final[dict[CategoryKey, str]] = {
    "unknownChecks": "Unknown type checks",
    "optionalChecks": "Optional member checks",
    "unusedSymbols": "Unused symbol warnings",
    "general": "General diagnostics",
}

_CATEGORY_PATTERN_LOOKUPS: Final[tuple[tuple[CategoryName, tuple[str, ...]], ...]] = tuple(
    (
        CategoryName(category),
        tuple(pattern.lower() for pattern in patterns if pattern),
    )
    for category, patterns in CATEGORY_PATTERNS.items()
    if category != str(GENERAL_CATEGORY)
)


class ReadinessEntry(TypedDict):
    path: str
    errors: int
    warnings: int
    information: int
    codeCounts: dict[str, int]
    categoryCounts: dict[CategoryKey, int]
    recommendations: list[str]


@dataclass(slots=True)
class ReadinessOptions:
    threshold: int
    buckets: dict[ReadinessStatus, tuple[ReadinessOptionEntry, ...]] = field(
        default_factory=lambda: dict.fromkeys(ReadinessStatus, ())
    )

    def add_entry(self, status: ReadinessStatus, entry: ReadinessOptionEntry) -> None:
        current = self.buckets.get(status, ())
        self.buckets[status] = (*current, entry)

    def to_payload(self) -> ReadinessOptionsPayload:
        buckets: dict[ReadinessStatus, tuple[ReadinessOptionEntry, ...]] = {
            status: entries for status, entries in self.buckets.items() if entries
        }
        return {
            "threshold": self.threshold,
            "buckets": buckets,
        }

    @classmethod
    def from_payload(
        cls,
        bucket: ReadinessOptionsPayload,
        *,
        default_threshold: int = DEFAULT_CLOSE_THRESHOLD,
    ) -> ReadinessOptions:
        threshold = bucket.get("threshold", default_threshold)
        instance = cls(threshold=threshold)
        source_map = cast("Mapping[object, object]", bucket.get("buckets", {}))
        for raw_status, raw_entries in source_map.items():
            if isinstance(raw_status, ReadinessStatus):
                status: ReadinessStatus = raw_status
            elif isinstance(raw_status, str):
                try:
                    status = ReadinessStatus.from_str(raw_status)
                except ValueError:
                    continue
            else:
                continue
            if isinstance(raw_entries, tuple):
                instance.buckets[status] = cast(
                    tuple[ReadinessOptionEntry, ...],
                    raw_entries,
                )
            elif isinstance(raw_entries, list):
                typed_entries = cast(list[ReadinessOptionEntry], raw_entries)
                instance.buckets[status] = tuple(typed_entries)
        return instance


CategoryCountMap = dict[CategoryName, int]
CategoryStatusMap = dict[CategoryName, ReadinessStatus]
StrictBuckets = dict[ReadinessStatus, list[ReadinessStrictEntry]]
OptionsPayloads = dict[CategoryKey, ReadinessOptionsPayload]
ReadinessOptionsMap = dict[CategoryKey, ReadinessOptions]


class ReadinessPayload(TypedDict):
    strict: StrictBuckets
    options: OptionsPayloads


def _new_category_counts() -> CategoryCountMap:
    return dict.fromkeys(CATEGORY_NAMES, 0)


def _category_counts_from_entry(entry: ReadinessEntry) -> CategoryCountMap:
    raw_counts = entry.get("categoryCounts")
    if raw_counts:
        categories = _new_category_counts()
        general_extra = 0
        for category, count in raw_counts.items():
            try:
                count_int = int(count)
            except (TypeError, ValueError):
                continue
            category_key = CategoryName(category)
            increment = max(count_int, 0)
            if category_key in categories:
                categories[category_key] += increment
            else:
                general_extra += increment
        categories[GENERAL_CATEGORY] += general_extra
        return categories
    code_counts = entry.get("codeCounts", {})
    return _bucket_code_counts(code_counts)


def _category_status_map(categories: CategoryCountMap) -> CategoryStatusMap:
    status_map: CategoryStatusMap = {}
    for category_key in CATEGORY_PATTERNS:
        key = CategoryName(category_key)
        status_map[key] = _status_for_category(category_key, categories.get(key, 0))
    return status_map


def _append_option_buckets(  # noqa: PLR0913
    options: ReadinessOptionsMap,
    entry_path: str,
    category_status: CategoryStatusMap,
    categories: CategoryCountMap,
    errors: int,
    warnings: int,
) -> None:
    for category, status in category_status.items():
        category_key = cast(CategoryKey, str(category))
        bucket = options[category_key]
        entry_payload: ReadinessOptionEntry = {
            "path": entry_path,
            "count": categories.get(category, 0),
            "errors": errors,
            "warnings": warnings,
        }
        bucket.add_entry(status, entry_payload)


def _strict_status_details(
    total_diagnostics: int,
    category_status: CategoryStatusMap,
    categories: CategoryCountMap,
) -> tuple[ReadinessStatus, list[str]]:
    if total_diagnostics == 0:
        return ReadinessStatus.READY, []
    blocking_categories = [
        f"{category}"
        for category, status in category_status.items()
        if status is ReadinessStatus.BLOCKED and category != GENERAL_CATEGORY
    ]
    if total_diagnostics <= STRICT_CLOSE_THRESHOLD and not blocking_categories:
        notes = [
            f"{category!s}: {categories.get(category, 0)}"
            for category, status in category_status.items()
            if status is not ReadinessStatus.READY
        ]
        return ReadinessStatus.CLOSE, notes
    return ReadinessStatus.BLOCKED, []


def _build_strict_entry_payload(
    entry: ReadinessEntry,
    categories: CategoryCountMap,
    category_status: CategoryStatusMap,
    total_diagnostics: int,
    notes: list[str],
) -> ReadinessStrictEntry:
    strict_entry: ReadinessStrictEntry = {
        "path": entry["path"],
        "errors": entry.get("errors", 0),
        "warnings": entry.get("warnings", 0),
        "information": entry.get("information", 0),
        "diagnostics": total_diagnostics,
        "categories": {
            CategoryName(category): categories.get(CategoryName(category), 0)
            for category in CATEGORY_PATTERNS
        },
        "categoryStatus": dict(category_status.items()),
        "recommendations": entry.get("recommendations", []),
    }
    if notes:
        strict_entry["notes"] = notes
    return strict_entry


def _bucket_code_counts(code_counts: dict[str, int]) -> CategoryCountMap:
    buckets = _new_category_counts()
    for rule, count in code_counts.items():
        lowered = rule.lower()
        matched_category: CategoryName | None = None
        for category, patterns in _CATEGORY_PATTERN_LOOKUPS:
            if any(pattern in lowered for pattern in patterns):
                matched_category = category
                break
        if matched_category is None:
            matched_category = GENERAL_CATEGORY
        buckets[matched_category] += count
    return buckets


def _status_for_category(category: CategoryKey, count: int) -> ReadinessStatus:
    if count == 0:
        return ReadinessStatus.READY
    close_threshold = CATEGORY_CLOSE_THRESHOLD.get(category, DEFAULT_CLOSE_THRESHOLD)
    return ReadinessStatus.CLOSE if count <= close_threshold else ReadinessStatus.BLOCKED


def _new_options_bucket(category: CategoryKey) -> ReadinessOptions:
    threshold = CATEGORY_CLOSE_THRESHOLD.get(category, DEFAULT_CLOSE_THRESHOLD)
    return ReadinessOptions(threshold=threshold)


def _options_payload_from_map(options: ReadinessOptionsMap) -> OptionsPayloads:
    return {category: bucket.to_payload() for category, bucket in options.items()}


def compute_readiness(folder_entries: Sequence[ReadinessEntry]) -> ReadinessPayload:
    """Compute strict typing readiness for folders.

    Input folder_entries should contain keys: path, errors, warnings, information,
    and optionally codeCounts, recommendations.
    """
    strict_buckets: StrictBuckets = {status: [] for status in ReadinessStatus}
    option_buckets: ReadinessOptionsMap = {}
    for category in CATEGORY_PATTERNS:
        option_buckets[category] = _new_options_bucket(category)
    readiness: ReadinessPayload = {
        "strict": strict_buckets,
        "options": {},
    }

    for entry in folder_entries:
        categories = _category_counts_from_entry(entry)
        category_status = _category_status_map(categories)
        _append_option_buckets(
            option_buckets,
            entry_path=entry["path"],
            category_status=category_status,
            categories=categories,
            errors=entry.get("errors", 0),
            warnings=entry.get("warnings", 0),
        )

        total_diagnostics = entry.get("errors", 0) + entry.get("warnings", 0)
        strict_status, notes = _strict_status_details(
            total_diagnostics,
            category_status,
            categories,
        )
        strict_entry = _build_strict_entry_payload(
            entry,
            categories,
            category_status,
            total_diagnostics,
            notes,
        )
        readiness["strict"][strict_status].append(strict_entry)

    readiness["options"] = _options_payload_from_map(option_buckets)
    return readiness
