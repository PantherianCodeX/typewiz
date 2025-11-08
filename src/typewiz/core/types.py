# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from typewiz._internal.utils import JSONValue

from ..typed_manifest import EngineError, ToolSummary
from .model_types import SeverityLevel
from .type_aliases import Command, RelPath, ToolName

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from .model_types import CategoryMapping, Mode, OverrideEntry


def _default_raw_mapping() -> Mapping[str, JSONValue]:
    return {}


@dataclass(slots=True, frozen=True)
class Diagnostic:
    tool: ToolName
    severity: SeverityLevel
    path: Path
    line: int
    column: int
    code: str | None
    message: str
    raw: Mapping[str, JSONValue] = field(default_factory=_default_raw_mapping)


def _default_str_list() -> list[str]:
    return []


def _default_overrides_list() -> list[OverrideEntry]:
    return []


def _default_category_mapping() -> CategoryMapping:
    return {}


def _default_relpath_list() -> list[RelPath]:
    return []


@dataclass(slots=True)
class RunResult:
    tool: ToolName
    mode: Mode
    command: Command
    exit_code: int
    duration_ms: float
    diagnostics: list[Diagnostic]
    cached: bool = False
    profile: str | None = None
    config_file: Path | None = None
    plugin_args: list[str] = field(default_factory=_default_str_list)
    include: list[RelPath] = field(default_factory=_default_relpath_list)
    exclude: list[RelPath] = field(default_factory=_default_relpath_list)
    overrides: list[OverrideEntry] = field(default_factory=_default_overrides_list)
    category_mapping: CategoryMapping = field(default_factory=_default_category_mapping)
    # Optional: raw tool-provided summary counts (normalised to errors/warnings/information/total)
    tool_summary: ToolSummary | None = None
    scanned_paths: list[RelPath] = field(default_factory=_default_relpath_list)
    engine_error: EngineError | None = None

    def severity_counts(self) -> Counter[SeverityLevel]:
        counts: Counter[SeverityLevel] = Counter()
        for diag in self.diagnostics:
            counts[diag.severity] += 1
        return counts
