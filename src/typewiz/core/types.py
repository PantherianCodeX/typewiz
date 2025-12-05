# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Core data classes for type checking diagnostics and run results.

This module defines the primary dataclasses used to represent type checking
diagnostics and run results. These are the main data structures used internally
throughout Typewiz for storing and processing type checker output.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping
    from pathlib import Path

    from typewiz.manifest.typed import EngineError, ToolSummary
    from typewiz.runtime import JSONValue

    from .model_types import CategoryMapping, Mode, OverrideEntry, SeverityLevel
    from .type_aliases import Command, RelPath, ToolName


def _default_raw_mapping() -> Mapping[str, JSONValue]:
    """Create an empty mapping for diagnostic raw data.

    Returns:
        Empty dictionary for raw diagnostic data.
    """
    return {}


@dataclass(slots=True, frozen=True)
class Diagnostic:
    """Immutable dataclass representing a single type checking diagnostic.

    Attributes:
        tool: Name of the type checking tool that generated this diagnostic.
        severity: Severity level of the diagnostic (error, warning, or information).
        path: Absolute path to the file containing the diagnostic.
        line: Line number where the diagnostic occurs (1-indexed).
        column: Column number where the diagnostic occurs (1-indexed).
        code: Optional diagnostic rule code (e.g., 'type-error', 'unused-import').
        message: Human-readable diagnostic message.
        raw: Raw diagnostic data from the tool for additional context.
    """

    tool: ToolName
    severity: SeverityLevel
    path: Path
    line: int
    column: int
    code: str | None
    message: str
    raw: Mapping[str, JSONValue] = field(default_factory=_default_raw_mapping)


def _default_str_list() -> list[str]:
    """Create an empty string list.

    Returns:
        Empty list of strings.
    """
    return []


def _default_overrides_list() -> list[OverrideEntry]:
    """Create an empty override entries list.

    Returns:
        Empty list of OverrideEntry dictionaries.
    """
    return []


def _default_category_mapping() -> CategoryMapping:
    """Create an empty category mapping.

    Returns:
        Empty dictionary mapping category keys to rule lists.
    """
    return {}


def _default_relpath_list() -> list[RelPath]:
    """Create an empty relative path list.

    Returns:
        Empty list of relative paths.
    """
    return []


@dataclass(slots=True)
class RunResult:
    """Mutable dataclass representing the complete results of a type checking run.

    This class contains all information about a single execution of a type checker,
    including configuration, diagnostics found, and performance metrics.

    Attributes:
        tool: Name of the type checking tool used.
        mode: Execution mode (current or full).
        command: Full command line used to execute the tool.
        exit_code: Exit code returned by the type checker process.
        duration_ms: Execution duration in milliseconds.
        diagnostics: List of all diagnostics found during the run.
        cached: Whether results were retrieved from cache.
        profile: Optional type checking profile name used.
        config_file: Optional path to the type checker configuration file.
        plugin_args: Additional command-line arguments passed to the tool.
        include: List of paths included in type checking.
        exclude: List of paths excluded from type checking.
        overrides: Path-specific configuration overrides applied.
        category_mapping: Mapping of diagnostic categories to rule codes.
        tool_summary: Optional raw summary data from the type checker.
        scanned_paths: List of paths that were scanned during the run.
        engine_error: Optional error information if the engine failed.
    """

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
        """Calculate the count of diagnostics by severity level.

        Returns:
            Counter mapping each severity level to its diagnostic count.
        """
        counts: Counter[SeverityLevel] = Counter()
        for diag in self.diagnostics:
            counts[diag.severity] += 1
        return counts
