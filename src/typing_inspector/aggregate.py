from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

from .types import Diagnostic, RunResult


@dataclass(slots=True)
class FileSummary:
    path: str
    errors: int = 0
    warnings: int = 0
    information: int = 0
    diagnostics: list[dict] = field(default_factory=list)


@dataclass(slots=True)
class FolderSummary:
    path: str
    depth: int
    errors: int = 0
    warnings: int = 0
    information: int = 0
    code_counts: Counter[str] = field(default_factory=Counter)

    def to_dict(self) -> dict:
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
        return {
            "path": self.path,
            "depth": self.depth,
            "errors": self.errors,
            "warnings": self.warnings,
            "information": self.information,
            "codeCounts": dict(self.code_counts),
            "recommendations": recommendations,
        }


def summarise_run(run: RunResult, *, max_depth: int = 3) -> dict:
    files: dict[str, FileSummary] = {}
    folder_levels: dict[int, dict[str, FolderSummary]] = {depth: {} for depth in range(1, max_depth + 1)}

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
        summary.diagnostics.append(
            {
                "line": diag.line,
                "column": diag.column,
                "severity": diag.severity,
                "code": diag.code,
                "message": diag.message,
            }
        )

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

    file_list = sorted(files.values(), key=lambda item: (-item.errors, -item.warnings, item.path))
    folder_entries: list[dict] = []
    for depth in sorted(folder_levels):
        entries = sorted(
            folder_levels[depth].values(),
            key=lambda item: (-item.errors, -item.warnings, item.path),
        )
        folder_entries.extend(entry.to_dict() for entry in entries)

    return {
        "summary": {
            "errors": sum(1 for diag in run.diagnostics if diag.severity == "error"),
            "warnings": sum(1 for diag in run.diagnostics if diag.severity == "warning"),
            "information": sum(1 for diag in run.diagnostics if diag.severity not in {"error", "warning"}),
            "total": len(run.diagnostics),
        },
        "perFile": [asdict(item) for item in file_list],
        "perFolder": folder_entries,
    }
