# Copyright 2025 CrownOps Engineering
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Core readiness computation logic and data structures.

This module contains the core algorithms for computing readiness metrics,
including categorizing diagnostics, assessing status levels, and generating
readiness payloads for files and folders.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final, cast

from ratchetr.compat import TypedDict
from ratchetr.core.categories import CATEGORY_NAMES
from ratchetr.core.model_types import ReadinessStatus
from ratchetr.core.summary_types import (
    ReadinessOptionEntry,
    ReadinessOptionsPayload,
    ReadinessStrictEntry,
)
from ratchetr.core.type_aliases import CategoryKey, CategoryName

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

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
    """Input entry for readiness computation.

    Attributes:
        path (str): The file or folder path.
        errors (int): Number of error-level diagnostics.
        warnings (int): Number of warning-level diagnostics.
        information (int): Number of information-level diagnostics.
        codeCounts (dict[str, int]): Counts of specific diagnostic codes.
        categoryCounts (dict[CategoryKey, int]): Pre-categorized diagnostic counts.
        recommendations (list[str]): Suggested improvements for this path.
    """

    path: str
    errors: int
    warnings: int
    information: int
    # ignore JUSTIFIED: TypedDict fields must use camelCase to align with the JSON
    # readiness payload
    codeCounts: dict[str, int]  # noqa: FIX002, TD003  # TODO@PantherianCodeX: Restrict N815 ignores to JSON boundary after implementing schema validation
    # ignore JUSTIFIED: TypedDict fields must use camelCase to align with the JSON
    # readiness payload
    categoryCounts: dict[CategoryKey, int]  # noqa: FIX002, TD003  # TODO@PantherianCodeX: Restrict N815 ignores to JSON boundary after implementing schema validation
    recommendations: list[str]


@dataclass(slots=True)
class ReadinessOptions:
    """Readiness options tracking entries by status with a threshold.

    Attributes:
        threshold (int): The threshold for considering something "close" to ready.
        buckets (dict[ReadinessStatus, tuple[ReadinessOptionEntry, ...]]): Entries grouped by readiness status.
    """

    threshold: int
    buckets: dict[ReadinessStatus, tuple[ReadinessOptionEntry, ...]] = field(
        default_factory=lambda: dict.fromkeys(ReadinessStatus, ())
    )

    def add_entry(self, status: ReadinessStatus, entry: ReadinessOptionEntry) -> None:
        """Add an entry to the appropriate status bucket.

        Args:
            status (ReadinessStatus): The readiness status bucket to add to.
            entry (ReadinessOptionEntry): The entry to add.
        """
        current = self.buckets.get(status, ())
        self.buckets[status] = (*current, entry)

    def to_payload(self) -> ReadinessOptionsPayload:
        """Convert to a serializable payload.

        Returns:
            ReadinessOptionsPayload: A dictionary representation of the readiness options.
        """
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
        """Create ReadinessOptions from a payload dictionary.

        Args:
            bucket (ReadinessOptionsPayload): The payload to deserialize.
            default_threshold (int, optional): Default threshold if not in payload. Defaults to DEFAULT_CLOSE_THRESHOLD.

        Returns:
            ReadinessOptions: The deserialized readiness options instance.
        """
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
                    "tuple[ReadinessOptionEntry, ...]",
                    raw_entries,
                )
            elif isinstance(raw_entries, list):
                typed_entries = cast("list[ReadinessOptionEntry]", raw_entries)
                instance.buckets[status] = tuple(typed_entries)
        return instance


CategoryCountMap = dict[CategoryName, int]
CategoryStatusMap = dict[CategoryName, ReadinessStatus]
StrictBuckets = dict[ReadinessStatus, list[ReadinessStrictEntry]]
OptionsPayloads = dict[CategoryKey, ReadinessOptionsPayload]
ReadinessOptionsMap = dict[CategoryKey, ReadinessOptions]


class ReadinessPayload(TypedDict):
    """Complete readiness assessment payload.

    Attributes:
        strict (StrictBuckets): File-level readiness entries bucketed by status.
        options (OptionsPayloads): Folder-level readiness options by category.
    """

    strict: StrictBuckets
    options: OptionsPayloads


def _new_category_counts() -> CategoryCountMap:
    """Create a new category count map initialized to zero.

    Returns:
        CategoryCountMap: A dictionary with all categories initialized to 0.
    """
    return dict.fromkeys(CATEGORY_NAMES, 0)


def _category_counts_from_entry(entry: ReadinessEntry) -> CategoryCountMap:
    """Extract category counts from a readiness entry.

    Args:
        entry (ReadinessEntry): The readiness entry to process.

    Returns:
        CategoryCountMap: A mapping of categories to diagnostic counts.
    """
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
    """Determine readiness status for each category based on counts.

    Args:
        categories (CategoryCountMap): Diagnostic counts per category.

    Returns:
        CategoryStatusMap: A mapping of categories to their readiness status.
    """
    status_map: CategoryStatusMap = {}
    for category_key in CATEGORY_PATTERNS:
        key = CategoryName(category_key)
        status_map[key] = _status_for_category(category_key, categories.get(key, 0))
    return status_map


# ignore JUSTIFIED: helper consumes parallel aggregates; bundling planned
def _append_option_buckets(  # noqa: PLR0917, FIX002, TD003  # TODO@PantherianCodeX: Bundle counts/status into a dataclass to reduce positional args
    options: ReadinessOptionsMap,
    entry_path: str,
    category_status: CategoryStatusMap,
    categories: CategoryCountMap,
    errors: int,
    warnings: int,
) -> None:
    """Add entries to option buckets for each category.

    Args:
        options (ReadinessOptionsMap): The options map to update.
        entry_path (str): The path of the entry being processed.
        category_status (CategoryStatusMap): Status for each category.
        categories (CategoryCountMap): Diagnostic counts per category.
        errors (int): Total error count.
        warnings (int): Total warning count.
    """
    for category, status in category_status.items():
        category_key = cast("CategoryKey", str(category))
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
    """Determine strict readiness status and notes for an entry.

    Args:
        total_diagnostics (int): Total number of diagnostics.
        category_status (CategoryStatusMap): Status for each category.
        categories (CategoryCountMap): Diagnostic counts per category.

    Returns:
        tuple[ReadinessStatus, list[str]]: The overall status and any explanatory notes.
    """
    if not total_diagnostics:
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
    """Build a strict entry payload from computed data.

    Args:
        entry (ReadinessEntry): The original entry.
        categories (CategoryCountMap): Diagnostic counts per category.
        category_status (CategoryStatusMap): Status for each category.
        total_diagnostics (int): Total diagnostic count.
        notes (list[str]): Explanatory notes.

    Returns:
        ReadinessStrictEntry: A complete strict entry payload.
    """
    strict_entry: ReadinessStrictEntry = {
        "path": entry["path"],
        "errors": entry.get("errors", 0),
        "warnings": entry.get("warnings", 0),
        "information": entry.get("information", 0),
        "diagnostics": total_diagnostics,
        "categories": {
            CategoryName(category): categories.get(CategoryName(category), 0) for category in CATEGORY_PATTERNS
        },
        "categoryStatus": dict(category_status.items()),
        "recommendations": entry.get("recommendations", []),
    }
    if notes:
        strict_entry["notes"] = notes
    return strict_entry


def _bucket_code_counts(code_counts: dict[str, int]) -> CategoryCountMap:
    """Categorize diagnostic codes into predefined categories.

    Args:
        code_counts (dict[str, int]): Counts of specific diagnostic codes.

    Returns:
        CategoryCountMap: Diagnostic counts bucketed by category.
    """
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
    """Determine readiness status for a category based on its count.

    Args:
        category (CategoryKey): The category to assess.
        count (int): The diagnostic count for this category.

    Returns:
        ReadinessStatus: READY if count is 0, CLOSE if below threshold, BLOCKED otherwise.
    """
    if not count:
        return ReadinessStatus.READY
    close_threshold = CATEGORY_CLOSE_THRESHOLD.get(category, DEFAULT_CLOSE_THRESHOLD)
    return ReadinessStatus.CLOSE if count <= close_threshold else ReadinessStatus.BLOCKED


def _new_options_bucket(category: CategoryKey) -> ReadinessOptions:
    """Create a new ReadinessOptions bucket for a category.

    Args:
        category (CategoryKey): The category for which to create options.

    Returns:
        ReadinessOptions: A new options instance with category-specific threshold.
    """
    threshold = CATEGORY_CLOSE_THRESHOLD.get(category, DEFAULT_CLOSE_THRESHOLD)
    return ReadinessOptions(threshold=threshold)


def _options_payload_from_map(options: ReadinessOptionsMap) -> OptionsPayloads:
    """Convert an options map to a payload dictionary.

    Args:
        options (ReadinessOptionsMap): The options map to convert.

    Returns:
        OptionsPayloads: A dictionary of category options payloads.
    """
    return {category: bucket.to_payload() for category, bucket in options.items()}


def compute_readiness(folder_entries: Sequence[ReadinessEntry]) -> ReadinessPayload:
    """Compute strict typing readiness for folders.

    Args:
        folder_entries: Folder payloads containing path, severity counts, and
            optional metadata (`codeCounts`, `recommendations`).

    Returns:
        `ReadinessPayload` grouping folder status buckets and option payloads.
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
