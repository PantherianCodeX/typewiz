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
    "general": tuple(),
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


def _bucket_code_counts(code_counts: dict[str, int]) -> dict[str, int]:
    buckets = {category: 0 for category in CATEGORY_PATTERNS}
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
        raw_category_counts = entry.get("categoryCounts") or {}
        if raw_category_counts:
            categories = {category: 0 for category in CATEGORY_PATTERNS}
            general_extra = 0
            for category, count in raw_category_counts.items():
                try:
                    count_int = int(count)
                except (TypeError, ValueError):
                    continue
                if category in categories:
                    categories[category] += max(count_int, 0)
                else:
                    general_extra += max(count_int, 0)
            categories["general"] += general_extra
        else:
            code_counts = entry.get("codeCounts", {})
            categories = _bucket_code_counts(code_counts)

        class CategoryMeta(TypedDict):
            status: StatusName
            count: int

        category_status: dict[str, CategoryMeta] = {}
        for category in CATEGORY_PATTERNS:
            count = categories.get(category, 0)
            status = _status_for_category(category, count)
            category_status[category] = {"status": status, "count": count}
            bucket = readiness["options"][category]
            status_list = bucket[status]
            status_list.append(
                {
                    "path": entry["path"],
                    "count": count,
                    "errors": entry.get("errors", 0),
                    "warnings": entry.get("warnings", 0),
                }
            )

        total_diagnostics = entry.get("errors", 0) + entry.get("warnings", 0)
        if total_diagnostics == 0:
            strict_status: StatusName = "ready"
        else:
            blocking_categories: list[str] = [
                cat
                for cat, meta in category_status.items()
                if meta["status"] == "blocked" and cat != "general"
            ]
            if total_diagnostics <= STRICT_CLOSE_THRESHOLD and not blocking_categories:
                strict_status = "close"
            else:
                strict_status = "blocked"

        strict_entry: ReadinessStrictEntry = {
            "path": entry["path"],
            "errors": entry.get("errors", 0),
            "warnings": entry.get("warnings", 0),
            "information": entry.get("information", 0),
            "diagnostics": total_diagnostics,
            "categories": {cat: meta["count"] for cat, meta in category_status.items()},
            "categoryStatus": {cat: meta["status"] for cat, meta in category_status.items()},
            "recommendations": entry.get("recommendations", []),
        }
        if strict_status == "close":
            blockers = [
                f"{cat}: {category_status[cat]['count']}"
                for cat in category_status
                if category_status[cat]["status"] != "ready"
            ]
            if blockers:
                strict_entry["notes"] = blockers

        readiness["strict"][strict_status].append(strict_entry)

    return readiness
