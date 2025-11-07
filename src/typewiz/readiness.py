# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

from collections.abc import Sequence
from typing import Final, TypedDict

from .model_types import ReadinessStatus
from .type_aliases import CategoryKey, CategoryName

STATUSES: Final[tuple[ReadinessStatus, ...]] = tuple(ReadinessStatus)
STATUS_VALUES: Final[tuple[str, ...]] = tuple(status.value for status in STATUSES)
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

CATEGORY_KEYS: Final[tuple[CategoryKey, ...]] = tuple(CATEGORY_PATTERNS.keys())
CATEGORY_NAMES: Final[tuple[CategoryName, ...]] = tuple(CategoryName(key) for key in CATEGORY_KEYS)
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
    categoryCounts: dict[str, int]
    recommendations: list[str]


class ReadinessOptionEntry(TypedDict):
    path: str
    count: int
    errors: int
    warnings: int


class ReadinessOptionBucket(TypedDict):
    ready: list[ReadinessOptionEntry]
    close: list[ReadinessOptionEntry]
    blocked: list[ReadinessOptionEntry]
    threshold: int


class ReadinessStrictEntry(TypedDict, total=False):
    path: str
    errors: int
    warnings: int
    information: int
    diagnostics: int
    categories: dict[str, int]
    categoryStatus: dict[str, ReadinessStatus]
    recommendations: list[str]
    notes: list[str]


CategoryCountMap = dict[CategoryName, int]
CategoryStatusMap = dict[CategoryName, ReadinessStatus]
StrictBuckets = dict[str, list[ReadinessStrictEntry]]
OptionsBuckets = dict[str, ReadinessOptionBucket]


class ReadinessPayload(TypedDict):
    strict: StrictBuckets
    options: OptionsBuckets


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


def _append_option_buckets(
    options: OptionsBuckets,
    entry_path: str,
    category_status: CategoryStatusMap,
    categories: CategoryCountMap,
    errors: int,
    warnings: int,
) -> None:
    for category, status in category_status.items():
        bucket = options[str(category)]
        entry_payload: ReadinessOptionEntry = {
            "path": entry_path,
            "count": categories.get(category, 0),
            "errors": errors,
            "warnings": warnings,
        }
        if status is ReadinessStatus.READY:
            bucket["ready"].append(entry_payload)
        elif status is ReadinessStatus.CLOSE:
            bucket["close"].append(entry_payload)
        else:
            bucket["blocked"].append(entry_payload)


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
            category: categories.get(CategoryName(category), 0) for category in CATEGORY_PATTERNS
        },
        "categoryStatus": {str(category): status for category, status in category_status.items()},
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


def _empty_option_bucket(category: CategoryKey) -> ReadinessOptionBucket:
    return {
        ReadinessStatus.READY.value: [],
        ReadinessStatus.CLOSE.value: [],
        ReadinessStatus.BLOCKED.value: [],
        "threshold": CATEGORY_CLOSE_THRESHOLD.get(category, DEFAULT_CLOSE_THRESHOLD),
    }


def compute_readiness(folder_entries: Sequence[ReadinessEntry]) -> ReadinessPayload:
    """Compute strict typing readiness for folders.

    Input folder_entries should contain keys: path, errors, warnings, information,
    and optionally codeCounts, recommendations.
    """
    readiness: ReadinessPayload = {
        "strict": {status_value: [] for status_value in STATUS_VALUES},
        "options": {category: _empty_option_bucket(category) for category in CATEGORY_PATTERNS},
    }

    for entry in folder_entries:
        categories = _category_counts_from_entry(entry)
        category_status = _category_status_map(categories)
        _append_option_buckets(
            readiness["options"],
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
        readiness["strict"][strict_status.value].append(strict_entry)

    return readiness
