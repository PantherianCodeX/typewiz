from __future__ import annotations

from typing import Any, Dict, List, Sequence, cast, TypedDict

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


def _bucket_code_counts(code_counts: Dict[str, int]) -> Dict[str, int]:
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


def _status_for_category(category: str, count: int) -> str:
    if count == 0:
        return "ready"
    close_threshold = CATEGORY_CLOSE_THRESHOLD.get(category, 3)
    return "close" if count <= close_threshold else "blocked"


class ReadinessEntry(TypedDict):
    path: str
    errors: int
    warnings: int
    information: int
    codeCounts: Dict[str, int]
    categoryCounts: Dict[str, int]
    recommendations: List[str]


def compute_readiness(folder_entries: Sequence[ReadinessEntry]) -> Dict[str, Any]:
    """Compute strict typing readiness for folders.

    Input folder_entries should contain keys: path, errors, warnings, information,
    and optionally codeCounts, recommendations.
    """
    readiness: Dict[str, Any] = {
        "strict": {"ready": [], "close": [], "blocked": []},
        "options": {
            category: {
                "ready": [],
                "close": [],
                "blocked": [],
                "threshold": CATEGORY_CLOSE_THRESHOLD.get(category, 3),
            }
            for category in CATEGORY_PATTERNS
        },
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
            status: str
            count: int
        category_status: Dict[str, CategoryMeta] = {}
        for category in CATEGORY_PATTERNS:
            count = categories.get(category, 0)
            status = _status_for_category(category, count)
            category_status[category] = {"status": status, "count": count}
            options_bucket = cast(Dict[str, Any], readiness["options"][category])
            status_list = cast(List[Dict[str, Any]], options_bucket[status])
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
            strict_status = "ready"
        else:
            blocking_categories: List[str] = [
                cat
                for cat, meta in category_status.items()
                if meta["status"] == "blocked" and cat != "general"
            ]
            if total_diagnostics <= STRICT_CLOSE_THRESHOLD and not blocking_categories:
                strict_status = "close"
            else:
                strict_status = "blocked"

        strict_entry: Dict[str, Any] = {
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

        strict_bucket = cast(List[Dict[str, Any]], readiness["strict"][strict_status])
        strict_bucket.append(strict_entry)

    return readiness
