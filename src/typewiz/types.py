from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Counter


@dataclass(slots=True)
class Diagnostic:
    tool: str
    severity: str
    path: Path
    line: int
    column: int
    code: str | None
    message: str
    raw: dict[str, Any] = field(default_factory=dict)

    def category(self) -> str:
        code = (self.code or "").lower()
        if "unknown" in code:
            return "unknown"
        if "optional" in code:
            return "optional"
        if "warnunused" in code:
            return "unused"
        return "general"


@dataclass(slots=True)
class RunResult:
    tool: str
    mode: str
    command: list[str]
    exit_code: int
    duration_ms: float
    diagnostics: list[Diagnostic]
    cached: bool = False
    profile: str | None = None
    config_file: Path | None = None
    plugin_args: list[str] = field(default_factory=list)
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    overrides: list[dict[str, object]] = field(default_factory=list)
    category_mapping: dict[str, list[str]] = field(default_factory=dict)

    def severity_counts(self) -> Counter[str]:
        counts: Counter[str] = Counter()
        for diag in self.diagnostics:
            counts[diag.severity.lower()] += 1
        return counts
