from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, cast

from .typed_manifest import (
    AggregatedData,
    FileDiagnostic,
    FileEntry,
    FolderEntry,
)
from .types import Diagnostic, RunResult


@dataclass(slots=True)
class FileSummary:
    path: str
    errors: int = 0
    warnings: int = 0
    information: int = 0
    diagnostics: list[FileDiagnostic] = field(default_factory=list)


@dataclass(slots=True)
class FolderSummary:
    path: str
    depth: int
    errors: int = 0
    warnings: int = 0
    information: int = 0
    code_counts: Counter[str] = field(default_factory=Counter)

    def to_folder_entry(self) -> FolderEntry:
        total = self.errors + self.warnings + self.information
        unknown = sum(count for code, count in self.code_counts.items() if "unknown" in code.lower())
        optional = sum(count for code, count in self.code_counts.items() if "optional" in code.lower())
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
            FolderEntry,
            {
                "path": self.path,
                "depth": self.depth,
                "errors": self.errors,
                "warnings": self.warnings,
                "information": self.information,
                "codeCounts": dict(self.code_counts),
                "recommendations": recommendations,
            },
        )


def summarise_run(run: RunResult, *, max_depth: int = 3) -> AggregatedData:
    files: dict[str, FileSummary] = {}
    folder_levels: dict[int, dict[str, FolderSummary]] = {depth: {} for depth in range(1, max_depth + 1)}

    severity_totals: Counter[str] = Counter()
    rule_totals: Counter[str] = Counter()

    for diag in run.diagnostics:
        rel_path = str(diag.path).replace("\\", "/")
        summary = files.get(rel_path)
        if summary is None:
            summary = FileSummary(path=rel_path)
            files[rel_path] = summary
        if diag.severity == "error":
            summary.errors += 1
        elif diag.severity == "warning":
            summary.warnings += 1
        else:
            summary.information += 1
        severity_totals[diag.severity] += 1
        if diag.code:
            rule_totals[diag.code] += 1

        file_diag: FileDiagnostic = {
            "line": diag.line,
            "column": diag.column,
            "severity": diag.severity,
            "code": diag.code,
            "message": diag.message,
        }
        summary.diagnostics.append(file_diag)

        parts = [part for part in Path(rel_path).parts if part not in {".", ""}]
        for depth in range(1, min(len(parts), max_depth) + 1):
            folder = "/".join(parts[:depth])
            level = folder_levels.setdefault(depth, {})
            bucket = level.get(folder)
            if bucket is None:
                bucket = FolderSummary(path=folder, depth=depth)
                level[folder] = bucket
            if diag.severity == "error":
                bucket.errors += 1
            elif diag.severity == "warning":
                bucket.warnings += 1
            else:
                bucket.information += 1
            if diag.code:
                bucket.code_counts[diag.code] += 1

    for summary in files.values():
        summary.diagnostics.sort(key=lambda entry: (entry["line"], entry["column"]))

    file_list = sorted(files.values(), key=lambda item: item.path)
    folder_entries: list[FolderEntry] = []
    for depth in sorted(folder_levels):
        entries = sorted(folder_levels[depth].values(), key=lambda item: item.path)
        folder_entries.extend(entry.to_folder_entry() for entry in entries)

    per_file: List[FileEntry] = [
        cast(
            FileEntry,
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

    return AggregatedData(
        summary={
            "errors": sum(1 for diag in run.diagnostics if diag.severity == "error"),
            "warnings": sum(1 for diag in run.diagnostics if diag.severity == "warning"),
            "information": sum(1 for diag in run.diagnostics if diag.severity not in {"error", "warning"}),
            "total": len(run.diagnostics),
            "severityBreakdown": {key: severity_totals[key] for key in sorted(severity_totals)},
            "ruleCounts": {key: rule_totals[key] for key in sorted(rule_totals)},
        },
        perFile=per_file,
        perFolder=folder_entries,
    )
