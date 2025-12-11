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

"""Base engine protocol and data structures for type checker engines.

This module defines the core abstractions for type checker engines in ratchetr,
including the BaseEngine protocol that all engines must implement, and the
supporting data structures for configuration (EngineOptions, EngineContext)
and results (EngineResult).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

from ratchetr.core.model_types import CategoryMapping, LogComponent, Mode, OverrideEntry
from ratchetr.logging import structured_extra

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from ratchetr.config import AuditConfig
    from ratchetr.core.type_aliases import Command, ProfileName, RelPath, ToolName
    from ratchetr.core.types import Diagnostic
    from ratchetr.manifest.typed import ToolSummary

logger: logging.Logger = logging.getLogger("ratchetr.engine")


def _default_overrides() -> list[OverrideEntry]:
    """Provide default empty overrides list for EngineOptions.

    Returns:
        list[OverrideEntry]: An empty list of override entries.
    """
    return []


def _default_category_mapping() -> CategoryMapping:
    """Provide default empty category mapping for EngineOptions.

    Returns:
        CategoryMapping: An empty dictionary for category mappings.
    """
    return {}


@dataclass(slots=True, frozen=True)
class EngineOptions:
    """Configuration options for running a type checker engine.

    This class encapsulates all the configuration needed to customize how a type
    checker engine runs, including command-line arguments, config files, path
    filters, and diagnostic categorization.

    Attributes:
        plugin_args: Additional command-line arguments to pass to the type checker.
        config_file: Optional path to a type checker configuration file.
        include: List of relative paths to include in the type check.
        exclude: List of relative paths to exclude from the type check.
        profile: Optional profile name for configuration selection.
        overrides: List of override entries for customizing diagnostic handling.
        category_mapping: Mapping of diagnostic categories to rule patterns.
    """

    plugin_args: list[str]
    config_file: Path | None
    include: list[RelPath]
    exclude: list[RelPath]
    profile: ProfileName | None
    overrides: list[OverrideEntry] = field(default_factory=_default_overrides)
    category_mapping: CategoryMapping = field(default_factory=_default_category_mapping)


@dataclass(slots=True, frozen=True)
class EngineContext:
    """Execution context for running a type checker engine.

    This class bundles together the project environment and configuration needed
    for an engine to execute properly, including the project root directory,
    audit settings, execution mode, and engine-specific options.

    Attributes:
        project_root: Root directory of the project being analyzed.
        audit_config: ratchetr audit configuration for the project.
        mode: Execution mode (e.g., CURRENT for full project, DELTA for changes).
        engine_options: Engine-specific configuration options.
    """

    project_root: Path
    audit_config: AuditConfig
    mode: Mode
    engine_options: EngineOptions


@dataclass(slots=True)
class EngineResult:
    """Results from running a type checker engine.

    This class captures all information about a type checker engine's execution,
    including diagnostics, performance metrics, and metadata. It performs validation
    in __post_init__ to warn about suspicious values.

    Attributes:
        engine: Name of the type checker engine that produced the results.
        mode: Execution mode used (CURRENT or DELTA).
        command: The exact command that was executed.
        exit_code: Exit code returned by the type checker process.
        duration_ms: Time taken to execute in milliseconds.
        diagnostics: List of diagnostic issues found by the type checker.
        cached: Whether these results came from cache rather than a fresh run.
        tool_summary: Optional summary counts from the tool itself (errors/warnings/info).
    """

    engine: ToolName
    mode: Mode
    command: Command
    exit_code: int
    duration_ms: float
    diagnostics: list[Diagnostic]
    cached: bool = False
    # Optional: raw tool-provided summary counts (normalised to errors/warnings/information/total)
    tool_summary: ToolSummary | None = None

    def __post_init__(self) -> None:
        """Validate result values and log warnings for suspicious data.

        This method checks for empty commands, negative durations, and negative
        exit codes, logging warnings when such issues are detected.
        """
        if not self.command:
            logger.warning(
                "Engine '%s' returned an empty command",
                self.engine,
                extra=structured_extra(component=LogComponent.ENGINE, tool=self.engine),
            )
        if self.duration_ms < 0:
            logger.warning(
                "Engine '%s' reported negative duration %.2f ms",
                self.engine,
                self.duration_ms,
                extra=structured_extra(component=LogComponent.ENGINE, tool=self.engine),
            )
        if self.exit_code < 0:
            logger.warning(
                "Engine '%s' returned negative exit code %s",
                self.engine,
                self.exit_code,
                extra=structured_extra(component=LogComponent.ENGINE, tool=self.engine),
            )


class BaseEngine(Protocol):
    """Protocol defining the interface that all type checker engines must implement.

    Any type checker engine (builtin or plugin) must conform to this protocol,
    providing a name attribute and implementing the run method. The optional
    category_mapping and fingerprint_targets methods provide additional metadata
    for diagnostic categorization and cache invalidation.

    Attributes:
        name: Unique identifier for the engine (e.g., "mypy", "pyright").
    """

    name: str

    # ignore JUSTIFIED: protocol method must document the EngineResult contract beyond
    # the return annotation
    def run(  # pylint: disable=redundant-returns-doc
        self,
        context: EngineContext,
        paths: Sequence[RelPath],
    ) -> EngineResult:
        """Execute the type checker engine on the specified paths.

        Args:
            context: Execution context including project root and configuration.
            paths: Sequence of relative paths to analyze.

        Returns:
            EngineResult: Aggregated engine results containing diagnostics for all
            analysed paths, the engine's exit code, and timing metadata.
        """
        # ignore JUSTIFIED: protocol stub uses ellipsis and is excluded from coverage;
        # concrete engine implementations are tested instead
        ...  # pragma: no cover  # pylint: disable=unnecessary-ellipsis

    @staticmethod
    def category_mapping() -> CategoryMapping:
        """Provide mapping from diagnostic categories to rule patterns.

        This optional method returns a dictionary mapping category names
        (e.g., "unknownChecks", "optionalChecks") to lists of rule code
        substrings used for readiness analysis.

        Returns:
            CategoryMapping: Mapping from category names to rule code patterns
            used to group diagnostics for readiness analysis. Implementations
            may return an empty mapping if no custom categorisation is needed.
        """
        return {}

    def fingerprint_targets(
        self,
        context: EngineContext,
        paths: Sequence[RelPath],
    ) -> Sequence[str]:
        """Specify additional files that should invalidate cached results.

        This optional method returns paths or globs for files whose changes
        should trigger cache invalidation (e.g., config files). Used to ensure
        cached results are invalidated when relevant configuration changes.

        Args:
            context: Execution context including project root and configuration.
            paths: Sequence of relative paths being analyzed.

        Returns:
            Sequence[str]: List of file paths or globs that affect caching.
                Empty sequence if no additional fingerprinting is needed.
        """
        # Default implementation does not use context or paths but keeps a
        # consistent instance method shape for subclasses.
        _ = self
        del context, paths
        return []
