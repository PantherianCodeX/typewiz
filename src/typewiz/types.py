# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .model_types import SeverityLevel
from .typed_manifest import EngineError, ToolSummary

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from .model_types import CategoryMapping, Mode, OverrideEntry


def _default_raw_mapping() -> Mapping[str, object]:
    return {}


@dataclass(slots=True)
class Diagnostic:
    tool: str
    severity: SeverityLevel
    path: Path
    line: int
    column: int
    code: str | None
    message: str
    raw: Mapping[str, object] = field(default_factory=_default_raw_mapping)

    def category(self) -> str:
        code = (self.code or "").lower()
        if "unknown" in code:
            return "unknown"
        if "optional" in code:
            return "optional"
        if "warnunused" in code:
            return "unused"
        return "general"


def _default_str_list() -> list[str]:
    return []


def _default_overrides_list() -> list[OverrideEntry]:
    return []


def _default_category_mapping() -> CategoryMapping:
    return {}


@dataclass(slots=True)
class RunResult:
    tool: str
    mode: Mode
    command: list[str]
    exit_code: int
    duration_ms: float
    diagnostics: list[Diagnostic]
    cached: bool = False
    profile: str | None = None
    config_file: Path | None = None
    plugin_args: list[str] = field(default_factory=_default_str_list)
    include: list[str] = field(default_factory=_default_str_list)
    exclude: list[str] = field(default_factory=_default_str_list)
    overrides: list[OverrideEntry] = field(default_factory=_default_overrides_list)
    category_mapping: CategoryMapping = field(default_factory=_default_category_mapping)
    # Optional: raw tool-provided summary counts (normalised to errors/warnings/information/total)
    tool_summary: ToolSummary | None = None
    scanned_paths: list[str] = field(default_factory=_default_str_list)
    engine_error: EngineError | None = None

    def severity_counts(self) -> Counter[str]:
        counts: Counter[str] = Counter()
        for diag in self.diagnostics:
            counts[diag.severity.value] += 1
        return counts
