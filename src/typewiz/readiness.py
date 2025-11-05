from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, TypedDict

from .type_aliases import CategoryName

# Category patterns and thresholds can be tuned here without touching renderers
CATEGORY_PATTERNS: dict[str, tuple[str, ...]] = {
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

CATEGORY_CLOSE_THRESHOLD = {
    "unknownChecks": 2,
    "optionalChecks": 2,
    "unusedSymbols": 4,
    "general": 5,
}

STRICT_CLOSE_THRESHOLD = 3

CATEGORY_LABELS = {
    "unknownChecks": "Unknown type checks",
    "optionalChecks": "Optional member checks",
    "unusedSymbols": "Unused symbol warnings",
    "general": "General diagnostics",
}

CategoryCountMap = dict[CategoryName, int]
CategoryStatusMap = dict[CategoryName, "StatusName"]


def _category_counts_from_entry(entry: ReadinessEntry) -> CategoryCountMap:
    raw_counts = entry.get("categoryCounts")
    if raw_counts:
        categories: CategoryCountMap = {CategoryName(name): 0 for name in CATEGORY_PATTERNS}
        general_extra = 0
        for category, count in raw_counts.items():
            try:
                count_int = int(count)
            except (TypeError, ValueError):
                continue
            category_key = CategoryName(category)
            if category_key in categories:
                categories[category_key] += max(count_int, 0)
            else:
                general_extra += max(count_int, 0)
        categories[CategoryName("general")] += general_extra
        return categories
    code_counts = entry.get("codeCounts", {})
    return _bucket_code_counts(code_counts)


def _category_status_map(categories: CategoryCountMap) -> CategoryStatusMap:
    status_map: CategoryStatusMap = {}
    for category_name in CATEGORY_PATTERNS:
        key = CategoryName(category_name)
        status_map[key] = _status_for_category(category_name, categories.get(key, 0))
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
        bucket[status].append(
            {
                "path": entry_path,
                "count": categories.get(category, 0),
                "errors": errors,
                "warnings": warnings,
            }
        )


def _strict_status_details(
    total_diagnostics: int,
    category_status: CategoryStatusMap,
    categories: CategoryCountMap,
) -> tuple[StatusName, list[str]]:
    if total_diagnostics == 0:
        return "ready", []
    blocking_categories = [
        f"{category}"
        for category, status in category_status.items()
        if status == "blocked" and str(category) != "general"
    ]
    if total_diagnostics <= STRICT_CLOSE_THRESHOLD and not blocking_categories:
        notes = [
            f"{category!s}: {categories.get(category, 0)}"
            for category, status in category_status.items()
            if status != "ready"
        ]
        return "close", notes
    return "blocked", []


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
    buckets: CategoryCountMap = {CategoryName(name): 0 for name in CATEGORY_PATTERNS}
    for rule, count in code_counts.items():
        lowered = rule.lower()
        matched_category: CategoryName | None = None
        for category, patterns in CATEGORY_PATTERNS.items():
            if category == "general":
                continue
            if any(pattern in lowered for pattern in patterns):
                matched_category = CategoryName(category)
                break
        if matched_category is None:
            matched_category = CategoryName("general")
        buckets[matched_category] += count
    return buckets


StatusName = Literal["ready", "close", "blocked"]
STATUSES: tuple[StatusName, StatusName, StatusName] = ("ready", "close", "blocked")


def _status_for_category(category: str, count: int) -> StatusName:
    if count == 0:
        return "ready"
    close_threshold = CATEGORY_CLOSE_THRESHOLD.get(category, 3)
    return "close" if count <= close_threshold else "blocked"


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
    categoryStatus: dict[str, StatusName]
    recommendations: list[str]
    notes: list[str]


StrictBuckets = dict[StatusName, list[ReadinessStrictEntry]]
OptionsBuckets = dict[str, ReadinessOptionBucket]


class ReadinessPayload(TypedDict):
    strict: StrictBuckets
    options: OptionsBuckets


def _empty_option_bucket(category: str) -> ReadinessOptionBucket:
    return {
        "ready": [],
        "close": [],
        "blocked": [],
        "threshold": CATEGORY_CLOSE_THRESHOLD.get(category, 3),
    }


def compute_readiness(folder_entries: Sequence[ReadinessEntry]) -> ReadinessPayload:
    """Compute strict typing readiness for folders.

    Input folder_entries should contain keys: path, errors, warnings, information,
    and optionally codeCounts, recommendations.
    """
    readiness: ReadinessPayload = {
        "strict": {status: [] for status in STATUSES},
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
            total_diagnostics, category_status, categories
        )
        strict_entry = _build_strict_entry_payload(
            entry,
            categories,
            category_status,
            total_diagnostics,
            notes,
        )
        readiness["strict"][strict_status].append(strict_entry)

    return readiness
