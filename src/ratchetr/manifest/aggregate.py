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

"""Aggregate and summarize type checking diagnostics from run results.

This module processes raw diagnostic data from type checking tools and aggregates
it into structured summaries at the file and folder levels. It categorizes issues,
tracks counts by severity and rule, and generates recommendations for typing
improvements.
"""

from __future__ import annotations

import operator
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Final, cast

from ratchetr.core.categories import coerce_category_key
from ratchetr.core.model_types import RecommendationCode, SeverityLevel
from ratchetr.core.type_aliases import CategoryKey, CategoryName, RuleName
from ratchetr.readiness.compute import CATEGORY_PATTERNS

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from ratchetr.core.types import RunResult
    from ratchetr.manifest.typed import AggregatedData, FileDiagnostic, FileEntry, FolderEntry


def _default_file_diagnostics() -> list[FileDiagnostic]:
    """Create default empty list for file diagnostics.

    Returns:
        Empty list of FileDiagnostic objects.
    """
    return []


@dataclass(slots=True)
class FileSummary:
    """Summary of type checking diagnostics for a single file.

    Tracks error counts by severity level and stores individual diagnostic
    messages for detailed reporting.

    Attributes:
        path: Relative path to the file being summarized.
        errors: Count of error-level diagnostics.
        warnings: Count of warning-level diagnostics.
        information: Count of information-level diagnostics.
        diagnostics: List of individual diagnostic entries.
    """

    path: str
    errors: int = 0
    warnings: int = 0
    information: int = 0
    diagnostics: list[FileDiagnostic] = field(default_factory=_default_file_diagnostics)


def _default_counter_str() -> Counter[str]:
    """Create default empty Counter for string keys.

    Returns:
        Empty Counter with string keys.
    """
    return Counter()


def _default_counter_category() -> Counter[CategoryKey]:
    """Create default empty Counter for category keys.

    Returns:
        Empty Counter with CategoryKey keys.
    """
    return Counter()


@dataclass(slots=True)
class FolderSummary:
    """Summary of type checking diagnostics for a folder.

    Aggregates diagnostic counts and categorizes issues for all files within
    a folder at a specific depth. Generates recommendations based on the
    issue profile.

    Attributes:
        path: Relative path to the folder being summarized.
        depth: Depth level in the folder hierarchy (1 = top level).
        errors: Count of error-level diagnostics.
        warnings: Count of warning-level diagnostics.
        information: Count of information-level diagnostics.
        code_counts: Counter of diagnostic codes (e.g., "attr-defined").
        category_counts: Counter of issue categories (e.g., "unknownChecks").
    """

    path: str
    depth: int
    errors: int = 0
    warnings: int = 0
    information: int = 0
    code_counts: Counter[str] = field(default_factory=_default_counter_str)
    category_counts: Counter[CategoryKey] = field(default_factory=_default_counter_category)

    def _unknown_count(self) -> int:
        """Calculate count of unknown-type related issues.

        Returns:
            Number of unknown-type issues in this folder.
        """
        if self.category_counts:
            return self.category_counts.get("unknownChecks", 0)
        return sum(count for code, count in self.code_counts.items() if "unknown" in code.lower())

    def _optional_count(self) -> int:
        """Calculate count of optional-check related issues.

        Returns:
            Number of optional-check issues in this folder.
        """
        if self.category_counts:
            return self.category_counts.get("optionalChecks", 0)
        return sum(count for code, count in self.code_counts.items() if "optional" in code.lower())

    def to_folder_entry(self) -> FolderEntry:
        """Convert this summary to a FolderEntry TypedDict.

        Generates recommendations based on the diagnostic profile:
        - Strict-ready if no issues
        - Suggestions for enabling unknown/optional checks
        - Top 3 most common rules with counts

        Returns:
            FolderEntry dictionary containing all summary data and recommendations.
        """
        total = self.errors + self.warnings + self.information
        unknown = self._unknown_count()
        optional = self._optional_count()
        recommendations: list[str] = []
        if not total:
            recommendations.append(RecommendationCode.STRICT_READY.value)
        else:
            if not unknown:
                recommendations.append(
                    RecommendationCode.CANDIDATE_ENABLE_UNKNOWN_CHECKS.value,
                )
            else:
                recommendations.append(f"resolve {unknown} unknown-type issues")
            if not optional:
                recommendations.append(
                    RecommendationCode.CANDIDATE_ENABLE_OPTIONAL_CHECKS.value,
                )
            else:
                recommendations.append(f"resolve {optional} optional-check issues")
            top_rules = Counter(self.code_counts).most_common(3)
            for rule, count in top_rules:
                recommendations.append(f"{rule}:{count}")
        return cast(
            "FolderEntry",
            {
                "path": self.path,
                "depth": self.depth,
                "errors": self.errors,
                "warnings": self.warnings,
                "information": self.information,
                "codeCounts": dict(self.code_counts),
                "categoryCounts": dict(self.category_counts),
                "recommendations": recommendations,
            },
        )


def _canonical_category_mapping(
    mapping: Mapping[CategoryKey, Iterable[str]] | Mapping[CategoryName, Iterable[str]] | Mapping[str, Iterable[str]],
) -> dict[CategoryKey, tuple[str, ...]]:
    """Normalize and deduplicate category mapping patterns.

    Converts category keys to canonical form, lowercases all patterns,
    and removes duplicates while preserving order.

    Args:
        mapping: Dictionary mapping category keys/names to pattern lists.

    Returns:
        Canonical mapping with CategoryKey keys and deduplicated lowercase pattern tuples.
    """
    canonical: dict[CategoryKey, tuple[str, ...]] = {}
    for key, raw_values in mapping.items():
        category_key = coerce_category_key(key)
        if category_key is None:
            continue
        seen: set[str] = set()
        cleaned: list[str] = []
        for raw in raw_values:
            candidate = raw.strip()
            if not candidate:
                continue
            lowered = candidate.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            cleaned.append(lowered)
        if cleaned:
            canonical[category_key] = tuple(cleaned)
    return canonical


_GENERAL_CATEGORY: Final[CategoryKey] = "general"
_FALLBACK_CATEGORY_LOOKUPS: Final[tuple[tuple[CategoryKey, tuple[str, ...]], ...]] = tuple(
    (
        category,
        tuple(pattern.lower() for pattern in patterns if pattern),
    )
    for category, patterns in CATEGORY_PATTERNS.items()
    if category != _GENERAL_CATEGORY
)


def _build_category_lookup(
    mapping: Mapping[CategoryKey, Iterable[str]],
) -> tuple[tuple[CategoryKey, tuple[str, ...]], ...]:
    """Build tuple of category-pattern pairs for fast lookup.

    Args:
        mapping: Dictionary mapping category keys to pattern iterables.

    Returns:
        Tuple of (category, patterns) pairs with empty patterns filtered out.
    """
    lookups: list[tuple[CategoryKey, tuple[str, ...]]] = []
    for category, patterns in mapping.items():
        cleaned = tuple(pattern for pattern in patterns if pattern)
        if cleaned:
            lookups.append((category, cleaned))
    return tuple(lookups)


class _Categoriser:
    """Categorizes diagnostic codes into semantic categories.

    Uses custom and fallback pattern matching with caching for performance.
    """

    __slots__ = ("_cache", "_custom_lookup")

    def __init__(self, mapping: Mapping[CategoryKey, Iterable[str]]) -> None:
        """Initialize categoriser with custom category patterns.

        Args:
            mapping: Custom category to pattern mapping.
        """
        super().__init__()
        self._custom_lookup = _build_category_lookup(mapping)
        self._cache: dict[str, CategoryKey] = {}

    def categorise(self, code: str | None) -> CategoryKey:
        """Categorize a diagnostic code into a semantic category.

        First checks custom patterns, then falls back to default patterns.
        Results are cached for performance.

        Args:
            code: Diagnostic code to categorize (e.g., "attr-defined").

        Returns:
            CategoryKey representing the semantic category.
        """
        if not code:
            return _GENERAL_CATEGORY
        cached = self._cache.get(code)
        if cached is not None:
            return cached
        lowered = code.lower()
        for category, patterns in self._custom_lookup:
            if any(pattern in lowered for pattern in patterns):
                self._cache[code] = category
                return category
        for category, patterns in _FALLBACK_CATEGORY_LOOKUPS:
            if any(pattern in lowered for pattern in patterns):
                self._cache[code] = category
                return category
        self._cache[code] = _GENERAL_CATEGORY
        return _GENERAL_CATEGORY


def _normalise_rel_path(path: Path) -> str:
    """Normalize path separators to forward slashes.

    Args:
        path: Path to normalize.

    Returns:
        String path with forward slashes.
    """
    return str(path).replace("\\", "/")


def _ensure_file_summary(files: dict[str, FileSummary], rel_path: str) -> FileSummary:
    """Get or create a FileSummary for the given path.

    Args:
        files: Dictionary of existing file summaries.
        rel_path: Relative path to the file.

    Returns:
        FileSummary for the given path, newly created if needed.
    """
    summary = files.get(rel_path)
    if summary is None:
        summary = FileSummary(path=rel_path)
        files[rel_path] = summary
    return summary


_PATH_PART_CACHE: dict[str, tuple[str, ...]] = {}
_MAX_PATH_CACHE_SIZE: Final[int] = 4096


def _split_rel_path(rel_path: str) -> tuple[str, ...]:
    """Split path into parts with caching for performance.

    Args:
        rel_path: Relative path string to split.

    Returns:
        Tuple of path components, excluding "." and empty strings.
    """
    cached = _PATH_PART_CACHE.get(rel_path)
    if cached is not None:
        return cached
    parts = tuple(part for part in Path(rel_path).parts if part not in {".", ""})
    if len(_PATH_PART_CACHE) >= _MAX_PATH_CACHE_SIZE:
        _PATH_PART_CACHE.clear()
    _PATH_PART_CACHE[rel_path] = parts
    return parts


# ignore JUSTIFIED: summary helper updates several global counters in one place;
# extra wrapper objects would harm readability
def _update_file_summary(  # noqa: PLR0913
    summary: FileSummary,
    *,
    severity: SeverityLevel,
    code: str | None,
    diagnostic: FileDiagnostic,
    severity_totals: Counter[SeverityLevel],
    rule_totals: Counter[RuleName],
    category_totals: Counter[CategoryKey],
    categoriser: _Categoriser,
) -> CategoryKey:
    """Update file summary and global totals with a new diagnostic.

    Args:
        summary: FileSummary to update.
        severity: Severity level of the diagnostic.
        code: Diagnostic code (e.g., "attr-defined").
        diagnostic: FileDiagnostic entry to append.
        severity_totals: Global counter for severity levels.
        rule_totals: Global counter for rule names.
        category_totals: Global counter for categories.
        categoriser: Categoriser instance for code categorization.

    Returns:
        CategoryKey assigned to this diagnostic.
    """
    if severity is SeverityLevel.ERROR:
        summary.errors += 1
    elif severity is SeverityLevel.WARNING:
        summary.warnings += 1
    else:
        summary.information += 1
    summary.diagnostics.append(diagnostic)
    severity_totals[severity] += 1
    if code:
        rule_totals[RuleName(code)] += 1
    category = categoriser.categorise(code)
    category_totals[category] += 1
    return category


def _folder_summaries_for_path(
    folder_levels: dict[int, dict[str, FolderSummary]],
    rel_path: str,
    max_depth: int,
) -> Iterable[FolderSummary]:
    """Get or create FolderSummary objects for all ancestor folders.

    Creates folder summaries for each depth level from 1 to max_depth
    along the path hierarchy.

    Args:
        folder_levels: Nested dict mapping depth -> folder path -> FolderSummary.
        rel_path: Relative path to the file.
        max_depth: Maximum folder depth to track.

    Yields:
        FolderSummary for each ancestor folder up to max_depth.
    """
    parts = _split_rel_path(rel_path)
    for depth in range(1, min(len(parts), max_depth) + 1):
        folder = "/".join(parts[:depth])
        level = folder_levels.setdefault(depth, {})
        bucket = level.get(folder)
        if bucket is None:
            bucket = FolderSummary(path=folder, depth=depth)
            level[folder] = bucket
        yield bucket


def _update_folder_summary(
    bucket: FolderSummary,
    *,
    severity: SeverityLevel,
    code: str | None,
    category: CategoryKey,
) -> None:
    """Update folder summary counters with a diagnostic.

    Args:
        bucket: FolderSummary to update.
        severity: Severity level of the diagnostic.
        code: Diagnostic code.
        category: Category assigned to the diagnostic.
    """
    if severity is SeverityLevel.ERROR:
        bucket.errors += 1
    elif severity is SeverityLevel.WARNING:
        bucket.warnings += 1
    else:
        bucket.information += 1
    if code:
        bucket.code_counts[code] += 1
    bucket.category_counts[category] += 1


def _finalise_file_entries(files: dict[str, FileSummary]) -> list[FileEntry]:
    """Convert FileSummary objects to FileEntry dicts, sorted and ordered.

    Sorts diagnostics within each file by line and column, then sorts
    files by path.

    Args:
        files: Dictionary of FileSummary objects keyed by path.

    Returns:
        List of FileEntry dicts sorted by path.
    """
    for summary in files.values():
        summary.diagnostics.sort(key=operator.itemgetter("line", "column"))
    file_list = sorted(files.values(), key=lambda item: item.path)
    return [
        cast(
            "FileEntry",
            {
                "path": item.path,
                "errors": item.errors,
                "warnings": item.warnings,
                "information": item.information,
                "diagnostics": item.diagnostics,
            },
        )
        for item in file_list
    ]


def _finalise_folder_entries(
    folder_levels: dict[int, dict[str, FolderSummary]],
) -> list[FolderEntry]:
    """Convert FolderSummary objects to FolderEntry dicts, sorted by depth and path.

    Args:
        folder_levels: Nested dict mapping depth -> folder path -> FolderSummary.

    Returns:
        List of FolderEntry dicts sorted by depth then path.
    """
    folder_entries: list[FolderEntry] = []
    for depth in sorted(folder_levels):
        entries = sorted(folder_levels[depth].values(), key=lambda item: item.path)
        folder_entries.extend(entry.to_folder_entry() for entry in entries)
    return folder_entries


def _build_summary_counts(
    run: RunResult,
    *,
    severity_totals: Counter[SeverityLevel],
    rule_totals: Counter[RuleName],
    category_totals: Counter[CategoryKey],
) -> dict[str, object]:
    """Build summary statistics dictionary from run results and counters.

    Args:
        run: RunResult containing diagnostics.
        severity_totals: Counter of diagnostics by severity.
        rule_totals: Counter of diagnostics by rule name.
        category_totals: Counter of diagnostics by category.

    Returns:
        Dictionary with summary statistics including breakdowns by severity, rule, and category.
    """
    return {
        "errors": sum(1 for diag in run.diagnostics if diag.severity is SeverityLevel.ERROR),
        "warnings": sum(1 for diag in run.diagnostics if diag.severity is SeverityLevel.WARNING),
        "information": sum(1 for diag in run.diagnostics if diag.severity is SeverityLevel.INFORMATION),
        "total": len(run.diagnostics),
        "severityBreakdown": {
            severity: severity_totals[severity] for severity in sorted(severity_totals, key=lambda item: item.value)
        },
        "ruleCounts": {str(key): rule_totals[key] for key in sorted(rule_totals, key=str)},
        "categoryCounts": {category: category_totals[category] for category in sorted(category_totals, key=str)},
    }


def summarise_run(run: RunResult, *, max_depth: int = 3) -> AggregatedData:
    """Aggregate and summarize diagnostics from a type checking run.

    Processes all diagnostics to create:
    - Overall summary statistics
    - Per-file diagnostic details
    - Per-folder aggregations with recommendations

    Args:
        run: RunResult containing diagnostics and configuration.
        max_depth: Maximum folder depth to aggregate (default: 3).

    Returns:
        AggregatedData containing summary, file entries, and folder entries.
    """
    files: dict[str, FileSummary] = {}
    folder_levels: dict[int, dict[str, FolderSummary]] = {depth: {} for depth in range(1, max_depth + 1)}

    severity_totals: Counter[SeverityLevel] = Counter()
    rule_totals: Counter[RuleName] = Counter()
    category_totals: Counter[CategoryKey] = Counter()
    category_mapping = _canonical_category_mapping(run.category_mapping)
    categoriser = _Categoriser(category_mapping)

    for diag in run.diagnostics:
        rel_path = _normalise_rel_path(diag.path)
        summary = _ensure_file_summary(files, rel_path)
        file_diag: FileDiagnostic = {
            "line": diag.line,
            "column": diag.column,
            "severity": diag.severity,
            "code": diag.code,
            "message": diag.message,
        }
        category = _update_file_summary(
            summary,
            severity=diag.severity,
            code=diag.code,
            diagnostic=file_diag,
            severity_totals=severity_totals,
            rule_totals=rule_totals,
            category_totals=category_totals,
            categoriser=categoriser,
        )
        for bucket in _folder_summaries_for_path(folder_levels, rel_path, max_depth):
            _update_folder_summary(
                bucket,
                severity=diag.severity,
                code=diag.code,
                category=category,
            )

    per_file = _finalise_file_entries(files)
    folder_entries = _finalise_folder_entries(folder_levels)

    return cast(
        "AggregatedData",
        {
            "summary": _build_summary_counts(
                run,
                severity_totals=severity_totals,
                rule_totals=rule_totals,
                category_totals=category_totals,
            ),
            "perFile": per_file,
            "perFolder": folder_entries,
        },
    )
