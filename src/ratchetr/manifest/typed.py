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

"""TypedDict definitions for manifest data structures.

This module provides typed dictionary structures that define the shape of
manifest data. These TypedDicts serve as the canonical type definitions,
with corresponding Pydantic models in models.py for runtime validation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ratchetr.compat.python import TypedDict

if TYPE_CHECKING:
    from ratchetr.core.model_types import CategoryMapping, Mode, OverrideEntry, SeverityLevel
    from ratchetr.core.type_aliases import CategoryKey, Command, RelPath


class FileDiagnostic(TypedDict):
    """A single diagnostic message within a file.

    Attributes:
        line: Line number where the diagnostic occurs (1-indexed).
        column: Column number where the diagnostic occurs (1-indexed).
        severity: Severity level (error, warning, or information).
        code: Optional diagnostic code (e.g., "attr-defined").
        message: Human-readable diagnostic message.
    """

    line: int
    column: int
    severity: SeverityLevel
    code: str | None
    message: str


class FileEntry(TypedDict):
    """File-level diagnostic summary.

    Attributes:
        path: Relative path to the file.
        errors: Count of error-level diagnostics.
        warnings: Count of warning-level diagnostics.
        information: Count of information-level diagnostics.
        diagnostics: List of individual diagnostics in this file.
    """

    path: str
    errors: int
    warnings: int
    information: int
    diagnostics: list[FileDiagnostic]


class FolderEntryRequired(TypedDict):
    """Required fields for folder-level diagnostic aggregation.

    Attributes:
        path: Relative path to the folder.
        depth: Depth level in the folder hierarchy (1 = top level).
        errors: Count of error-level diagnostics in this folder.
        warnings: Count of warning-level diagnostics in this folder.
        information: Count of information-level diagnostics in this folder.
        codeCounts: Dictionary mapping diagnostic codes to counts.
        recommendations: List of recommendations for improving typing health.
    """

    path: str
    depth: int
    errors: int
    warnings: int
    information: int
    codeCounts: dict[str, int]
    recommendations: list[str]


class FolderEntry(FolderEntryRequired, total=False):
    """Folder-level diagnostic aggregation with optional fields.

    Inherits all required fields from FolderEntryRequired.

    Attributes:
        categoryCounts: Optional dictionary mapping categories to counts.
    """

    categoryCounts: dict[CategoryKey, int]


class RunSummary(TypedDict, total=False):
    """Aggregated summary statistics for a type checking run.

    All fields are optional.

    Attributes:
        errors: Count of error-level diagnostics.
        warnings: Count of warning-level diagnostics.
        information: Count of information-level diagnostics.
        total: Total count of all diagnostics.
        severityBreakdown: Breakdown of counts by severity level.
        ruleCounts: Breakdown of counts by rule name.
        categoryCounts: Breakdown of counts by category.
    """

    errors: int
    warnings: int
    information: int
    total: int
    severityBreakdown: dict[SeverityLevel, int]
    ruleCounts: dict[str, int]
    categoryCounts: dict[CategoryKey, int]


class EngineOptionsEntry(TypedDict, total=False):
    """Engine configuration options for a type checking run.

    All fields are optional.

    Attributes:
        profile: Profile name (e.g., "strict", "standard").
        configFile: Path to the engine's config file.
        pluginArgs: List of additional command-line arguments.
        include: List of paths to include in type checking.
        exclude: List of paths to exclude from type checking.
        overrides: List of path or profile-specific overrides.
        categoryMapping: Mapping of categories to diagnostic code patterns.
    """

    profile: str | None
    configFile: str | None
    pluginArgs: list[str]
    include: list[RelPath]
    exclude: list[RelPath]
    overrides: list[OverrideEntry]
    categoryMapping: CategoryMapping


class ToolSummary(TypedDict, total=False):
    """Tool-reported summary statistics.

    Contains the summary counts as reported directly by the type checking tool.
    All fields are optional.

    Attributes:
        errors: Count of errors reported by the tool.
        warnings: Count of warnings reported by the tool.
        information: Count of informational messages reported by the tool.
        total: Total count of diagnostics reported by the tool.
    """

    errors: int
    warnings: int
    information: int
    total: int


class RunPayloadRequired(TypedDict):
    """Required fields for a type checking run payload.

    Attributes:
        tool: Name of the type checking tool (e.g., "mypy", "pyright").
        mode: Execution mode (e.g., "check", "watch").
        command: Full command that was executed.
        exitCode: Exit code from the engine process.
        durationMs: Duration of the run in milliseconds.
        summary: Aggregated summary statistics.
        perFile: List of file-level diagnostic summaries.
        perFolder: List of folder-level diagnostic aggregations.
        engineOptions: Engine configuration used for this run.
    """

    tool: str
    mode: Mode
    command: Command
    exitCode: int
    durationMs: float
    summary: RunSummary
    perFile: list[FileEntry]
    perFolder: list[FolderEntry]
    engineOptions: EngineOptionsEntry


class RunPayload(RunPayloadRequired, total=False):
    """Complete type checking run payload with optional fields.

    Inherits all required fields from RunPayloadRequired.

    Attributes:
        toolSummary: Summary as reported by the tool itself.
        engineArgsEffective: List of effective engine arguments.
        scannedPathsResolved: List of paths that were scanned.
        engineError: Error information if the engine failed.
    """

    toolSummary: ToolSummary
    engineArgsEffective: list[str]
    scannedPathsResolved: list[RelPath]
    engineError: EngineError


class EngineError(TypedDict, total=False):
    """Engine execution error information.

    All fields are optional.

    Attributes:
        message: Error message.
        exitCode: Exit code from the engine process.
        stderr: Standard error output from the engine.
    """

    message: str
    exitCode: int
    stderr: str


class ManifestData(TypedDict, total=False):
    """Top-level manifest structure.

    All fields are optional to support partial manifests.

    Attributes:
        generatedAt: ISO 8601 timestamp of manifest generation.
        projectRoot: Root directory of the project.
        schemaVersion: Manifest schema version string.
        toolVersions: Dictionary mapping tool names to version strings.
        fingerprintTruncated: Whether fingerprint data was truncated.
        runs: List of type checking runs included in this manifest.
    """

    # Manifest metadata
    generatedAt: str
    projectRoot: str
    schemaVersion: str
    toolVersions: dict[str, str]
    fingerprintTruncated: bool
    # Collected runs
    runs: list[RunPayload]


class AggregatedData(TypedDict):
    """Aggregated diagnostic data from a single run.

    Attributes:
        summary: Overall summary statistics.
        perFile: List of file-level diagnostic summaries.
        perFolder: List of folder-level diagnostic aggregations.
    """

    summary: RunSummary
    perFile: list[FileEntry]
    perFolder: list[FolderEntry]
