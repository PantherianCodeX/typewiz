from __future__ import annotations

from collections.abc import Sequence
from typing import Literal, TypedDict

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


def _category_counts_from_entry(entry: ReadinessEntry) -> dict[str, int]:
    raw_counts = entry.get("categoryCounts")
    if raw_counts:
        categories_init = dict.fromkeys(CATEGORY_PATTERNS, 0)
        categories = {key: int(value) for key, value in categories_init.items()}
        general_extra = 0
        for category, count in raw_counts.items():
            try:
                count_int = int(count)
            except (TypeError, ValueError):
                continue
            if category in categories:
                categories[category] += max(count_int, 0)
            else:
                general_extra += max(count_int, 0)
        categories["general"] += general_extra
        return categories
    code_counts = entry.get("codeCounts", {})
    return _bucket_code_counts(code_counts)


def _category_status_map(categories: dict[str, int]) -> dict[str, StatusName]:
    return {
        category: _status_for_category(category, categories.get(category, 0))
        for category in CATEGORY_PATTERNS
    }


def _append_option_buckets(
    options: OptionsBuckets,
    entry_path: str,
    category_status: dict[str, StatusName],
    categories: dict[str, int],
    errors: int,
    warnings: int,
) -> None:
    for category, status in category_status.items():
        bucket = options[category]
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
    category_status: dict[str, StatusName],
    categories: dict[str, int],
) -> tuple[StatusName, list[str]]:
    if total_diagnostics == 0:
        return "ready", []
    blocking_categories = [
        category
        for category, status in category_status.items()
        if status == "blocked" and category != "general"
    ]
    if total_diagnostics <= STRICT_CLOSE_THRESHOLD and not blocking_categories:
        notes = [
            f"{category}: {categories.get(category, 0)}"
            for category, status in category_status.items()
            if status != "ready"
        ]
        return "close", notes
    return "blocked", []


def _build_strict_entry_payload(
    entry: ReadinessEntry,
    categories: dict[str, int],
    category_status: dict[str, StatusName],
    total_diagnostics: int,
    notes: list[str],
) -> ReadinessStrictEntry:
    strict_entry: ReadinessStrictEntry = {
        "path": entry["path"],
        "errors": entry.get("errors", 0),
        "warnings": entry.get("warnings", 0),
        "information": entry.get("information", 0),
        "diagnostics": total_diagnostics,
        "categories": {category: categories.get(category, 0) for category in CATEGORY_PATTERNS},
        "categoryStatus": category_status,
        "recommendations": entry.get("recommendations", []),
    }
    if notes:
        strict_entry["notes"] = notes
    return strict_entry


def _bucket_code_counts(code_counts: dict[str, int]) -> dict[str, int]:
    buckets = dict.fromkeys(CATEGORY_PATTERNS, 0)
    for rule, count in code_counts.items():
        lowered = rule.lower()
        matched_category = None
        for category, patterns in CATEGORY_PATTERNS.items():
            if category == "general":
                continue
            if any(pattern in lowered for pattern in patterns):
                matched_category = category
                break
        if matched_category is None:
            matched_category = "general"
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
