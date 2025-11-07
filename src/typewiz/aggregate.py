# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

import operator
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Final, cast

from .model_types import SeverityLevel
from .readiness import CATEGORY_PATTERNS
from .type_aliases import CategoryKey, CategoryName, RuleName

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from .typed_manifest import AggregatedData, FileDiagnostic, FileEntry, FolderEntry
    from .types import RunResult


def _default_file_diagnostics() -> list[FileDiagnostic]:
    return []


@dataclass(slots=True)
class FileSummary:
    path: str
    errors: int = 0
    warnings: int = 0
    information: int = 0
    diagnostics: list[FileDiagnostic] = field(default_factory=_default_file_diagnostics)


def _default_counter_str() -> Counter[str]:
    return Counter()


@dataclass(slots=True)
class FolderSummary:
    path: str
    depth: int
    errors: int = 0
    warnings: int = 0
    information: int = 0
    code_counts: Counter[str] = field(default_factory=_default_counter_str)
    category_counts: Counter[str] = field(default_factory=_default_counter_str)

    def _unknown_count(self) -> int:
        if self.category_counts:
            return self.category_counts.get("unknownChecks", 0)
        return sum(count for code, count in self.code_counts.items() if "unknown" in code.lower())

    def _optional_count(self) -> int:
        if self.category_counts:
            return self.category_counts.get("optionalChecks", 0)
        return sum(count for code, count in self.code_counts.items() if "optional" in code.lower())

    def to_folder_entry(self) -> FolderEntry:
        total = self.errors + self.warnings + self.information
        unknown = self._unknown_count()
        optional = self._optional_count()
        recommendations: list[str] = []
        if total == 0:
            recommendations.append("strict-ready")
        else:
            if unknown == 0:
                recommendations.append("candidate-enable-unknown-checks")
            else:
                recommendations.append(f"resolve {unknown} unknown-type issues")
            if optional == 0:
                recommendations.append("candidate-enable-optional-checks")
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


def _canonical_category_mapping(mapping: Mapping[str, Iterable[str]]) -> dict[str, tuple[str, ...]]:
    canonical: dict[str, tuple[str, ...]] = {}
    for key, raw_values in mapping.items():
        key_str = key.strip()
        if not key_str:
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
            canonical[key_str] = tuple(cleaned)
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
    mapping: Mapping[str, Iterable[str]],
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    lookups: list[tuple[str, tuple[str, ...]]] = []
    for category, patterns in mapping.items():
        cleaned = tuple(pattern for pattern in patterns if pattern)
        if cleaned:
            lookups.append((category, cleaned))
    return tuple(lookups)


class _Categoriser:
    __slots__ = ("_cache", "_custom_lookup")

    def __init__(self, mapping: Mapping[str, Iterable[str]]) -> None:
        super().__init__()
        self._custom_lookup = _build_category_lookup(mapping)
        self._cache: dict[str, str] = {}

    def categorise(self, code: str | None) -> str:
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
    return str(path).replace("\\", "/")


def _ensure_file_summary(files: dict[str, FileSummary], rel_path: str) -> FileSummary:
    summary = files.get(rel_path)
    if summary is None:
        summary = FileSummary(path=rel_path)
        files[rel_path] = summary
    return summary


_PATH_PART_CACHE: dict[str, tuple[str, ...]] = {}
_MAX_PATH_CACHE_SIZE: Final[int] = 4096


def _split_rel_path(rel_path: str) -> tuple[str, ...]:
    cached = _PATH_PART_CACHE.get(rel_path)
    if cached is not None:
        return cached
    parts = tuple(part for part in Path(rel_path).parts if part not in {".", ""})
    if len(_PATH_PART_CACHE) >= _MAX_PATH_CACHE_SIZE:
        _PATH_PART_CACHE.clear()
    _PATH_PART_CACHE[rel_path] = parts
    return parts


def _update_file_summary(
    summary: FileSummary,
    *,
    severity: SeverityLevel,
    code: str | None,
    diagnostic: FileDiagnostic,
    severity_totals: Counter[str],
    rule_totals: Counter[RuleName],
    category_totals: Counter[CategoryName],
    categoriser: _Categoriser,
) -> str:
    if severity is SeverityLevel.ERROR:
        summary.errors += 1
    elif severity is SeverityLevel.WARNING:
        summary.warnings += 1
    else:
        summary.information += 1
    summary.diagnostics.append(diagnostic)
    severity_totals[severity.value] += 1
    if code:
        rule_totals[RuleName(code)] += 1
    category = categoriser.categorise(code)
    category_totals[CategoryName(category)] += 1
    return category


def _folder_summaries_for_path(
    folder_levels: dict[int, dict[str, FolderSummary]],
    rel_path: str,
    max_depth: int,
) -> Iterable[FolderSummary]:
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
    category: str,
) -> None:
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
    folder_entries: list[FolderEntry] = []
    for depth in sorted(folder_levels):
        entries = sorted(folder_levels[depth].values(), key=lambda item: item.path)
        folder_entries.extend(entry.to_folder_entry() for entry in entries)
    return folder_entries


def _build_summary_counts(
    run: RunResult,
    *,
    severity_totals: Counter[str],
    rule_totals: Counter[RuleName],
    category_totals: Counter[CategoryName],
) -> dict[str, object]:
    return {
        "errors": sum(1 for diag in run.diagnostics if diag.severity is SeverityLevel.ERROR),
        "warnings": sum(1 for diag in run.diagnostics if diag.severity is SeverityLevel.WARNING),
        "information": sum(
            1 for diag in run.diagnostics if diag.severity is SeverityLevel.INFORMATION
        ),
        "total": len(run.diagnostics),
        "severityBreakdown": {key: severity_totals[key] for key in sorted(severity_totals)},
        "ruleCounts": {str(key): rule_totals[key] for key in sorted(rule_totals, key=str)},
        "categoryCounts": {
            str(key): category_totals[key] for key in sorted(category_totals, key=str)
        },
    }


def summarise_run(run: RunResult, *, max_depth: int = 3) -> AggregatedData:
    files: dict[str, FileSummary] = {}
    folder_levels: dict[int, dict[str, FolderSummary]] = {
        depth: {} for depth in range(1, max_depth + 1)
    }

    severity_totals: Counter[str] = Counter()
    rule_totals: Counter[RuleName] = Counter()
    category_totals: Counter[CategoryName] = Counter()
    category_mapping = _canonical_category_mapping(run.category_mapping)
    categoriser = _Categoriser(category_mapping)

    for diag in run.diagnostics:
        rel_path = _normalise_rel_path(diag.path)
        summary = _ensure_file_summary(files, rel_path)
        file_diag: FileDiagnostic = {
            "line": diag.line,
            "column": diag.column,
            "severity": diag.severity.value,
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
