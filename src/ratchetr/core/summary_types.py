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

"""TypedDict definitions for summary and dashboard data structures.

This module defines TypedDict classes used for representing aggregated
type checking results, dashboard views, and summary data. These structures
are used for JSON serialization and dashboard rendering.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from ratchetr.compat import TypedDict

from .model_types import ReadinessStatus, SeverityLevel
from .type_aliases import CategoryKey, CategoryName, Command, RunId

if TYPE_CHECKING:
    from ratchetr.manifest.typed import EngineOptionsEntry, ToolSummary

CountsBySeverity = dict[SeverityLevel, int]
CountsByRule = dict[str, int]
CountsByCategory = dict[CategoryKey, int]


class SummaryRunEntry(TypedDict, total=False):
    """Summary data for a single type checking run.

    Attributes:
        command: Command used to execute the type checker.
        errors: Count of error-level diagnostics.
        warnings: Count of warning-level diagnostics.
        information: Count of informational diagnostics.
        total: Total count of all diagnostics.
        severityBreakdown: Breakdown of diagnostics by severity level.
        ruleCounts: Count of diagnostics per rule code.
        categoryCounts: Count of diagnostics per category.
        engineOptions: Engine configuration options used.
        toolSummary: Summary data from the type checking tool.
    """

    command: Command
    errors: int
    warnings: int
    information: int
    total: int
    severityBreakdown: CountsBySeverity
    ruleCounts: CountsByRule
    categoryCounts: CountsByCategory
    engineOptions: EngineOptionsEntry
    toolSummary: ToolSummary


class SummaryFolderEntry(TypedDict):
    """Summary data for a folder's type checking results.

    Attributes:
        path: Relative path to the folder.
        errors: Count of errors in the folder.
        warnings: Count of warnings in the folder.
        information: Count of informational diagnostics in the folder.
        participatingRuns: Number of runs that analyzed this folder.
        codeCounts: Count of diagnostics per error code.
        recommendations: List of recommendation codes for this folder.
    """

    path: str
    errors: int
    warnings: int
    information: int
    participatingRuns: int
    codeCounts: dict[str, int]
    recommendations: list[str]


class SummaryFileEntry(TypedDict):
    """Summary data for a file's type checking results.

    Attributes:
        path: Relative path to the file.
        errors: Count of errors in the file.
        warnings: Count of warnings in the file.
        information: Count of informational diagnostics in the file.
    """

    path: str
    errors: int
    warnings: int
    information: int


class RulePathEntry(TypedDict):
    """Entry linking a file path to diagnostic count for a specific rule.

    Attributes:
        path: Relative path to the file.
        count: Number of diagnostics for this rule in the file.
    """

    path: str
    count: int


class OverviewTab(TypedDict):
    """Dashboard overview tab data.

    Attributes:
        severityTotals: Total diagnostics by severity level.
        categoryTotals: Total diagnostics by category.
        runSummary: Summary data for each run.
    """

    severityTotals: CountsBySeverity
    categoryTotals: CountsByCategory
    runSummary: dict[RunId, SummaryRunEntry]


class EnginesTab(TypedDict):
    """Dashboard engines tab data.

    Attributes:
        runSummary: Summary data for each run grouped by engine.
    """

    runSummary: dict[RunId, SummaryRunEntry]


class HotspotsTab(TypedDict):
    """Dashboard hotspots tab data.

    Attributes:
        topRules: Most frequently occurring diagnostic rules.
        topFolders: Folders with the most diagnostics.
        topFiles: Files with the most diagnostics.
        ruleFiles: Files affected by each rule.
    """

    topRules: dict[str, int]
    topFolders: list[SummaryFolderEntry]
    topFiles: list[SummaryFileEntry]
    ruleFiles: dict[str, list[RulePathEntry]]


class ReadinessStrictEntry(TypedDict, total=False):
    """Entry for strict readiness analysis of a path.

    Attributes:
        path: Relative path being analyzed.
        diagnostics: Total count of diagnostics.
        notes: Human-readable notes about readiness.
        recommendations: List of recommendation codes.
        errors: Count of errors.
        warnings: Count of warnings.
        information: Count of informational diagnostics.
        categories: Diagnostic counts by category name.
        categoryStatus: Readiness status by category name.
    """

    path: str
    diagnostics: int
    notes: list[str]
    recommendations: list[str]
    errors: int
    warnings: int
    information: int
    categories: dict[CategoryName, int]
    categoryStatus: dict[CategoryName, ReadinessStatus]


class ReadinessOptionEntry(TypedDict, total=False):
    """Entry for optional readiness analysis category.

    Attributes:
        path: Relative path being analyzed.
        count: Count of diagnostics for the category.
        errors: Count of errors for the category.
        warnings: Count of warnings for the category.
    """

    path: str
    count: int
    errors: int
    warnings: int


class ReadinessOptionsPayload(TypedDict):
    """Payload for optional category readiness data.

    Attributes:
        threshold: Diagnostic count threshold for readiness.
        buckets: Entries grouped by readiness status.
    """

    threshold: int
    buckets: dict[ReadinessStatus, tuple[ReadinessOptionEntry, ...]]


class ReadinessTab(TypedDict, total=False):
    """Dashboard readiness tab data.

    Attributes:
        strict: Strict mode readiness entries by status.
        options: Optional category readiness data by category.
    """

    strict: dict[ReadinessStatus, list[ReadinessStrictEntry]]
    options: dict[CategoryKey, ReadinessOptionsPayload]


class RunsTab(TypedDict):
    """Dashboard runs tab data.

    Attributes:
        runSummary: Summary data for each run.
    """

    runSummary: dict[RunId, SummaryRunEntry]


class SummaryTabs(TypedDict):
    """Collection of all dashboard tab data.

    Attributes:
        overview: Overview tab data.
        engines: Engines tab data.
        hotspots: Hotspots tab data.
        readiness: Readiness tab data.
        runs: Runs tab data.
    """

    overview: OverviewTab
    engines: EnginesTab
    hotspots: HotspotsTab
    readiness: ReadinessTab
    runs: RunsTab


TAB_KEY_OVERVIEW: Final = "overview"
TAB_KEY_ENGINES: Final = "engines"
TAB_KEY_HOTSPOTS: Final = "hotspots"
TAB_KEY_READINESS: Final = "readiness"
TAB_KEY_RUNS: Final = "runs"


class SummaryData(TypedDict):
    """Complete summary data structure for type checking analysis.

    Attributes:
        generatedAt: ISO timestamp when the summary was generated.
        projectRoot: Absolute path to the project root.
        runSummary: Summary data for each run.
        severityTotals: Total diagnostics by severity.
        categoryTotals: Total diagnostics by category.
        topRules: Most frequently occurring rules.
        topFolders: Folders with the most diagnostics.
        topFiles: Files with the most diagnostics.
        ruleFiles: Files affected by each rule.
        tabs: Data for all dashboard tabs.
    """

    generatedAt: str
    projectRoot: str
    runSummary: dict[RunId, SummaryRunEntry]
    severityTotals: CountsBySeverity
    categoryTotals: CountsByCategory
    topRules: dict[str, int]
    topFolders: list[SummaryFolderEntry]
    topFiles: list[SummaryFileEntry]
    ruleFiles: dict[str, list[RulePathEntry]]
    tabs: SummaryTabs


__all__ = [
    "TAB_KEY_ENGINES",
    "TAB_KEY_HOTSPOTS",
    "TAB_KEY_OVERVIEW",
    "TAB_KEY_READINESS",
    "TAB_KEY_RUNS",
    "CountsByCategory",
    "CountsByRule",
    "CountsBySeverity",
    "EnginesTab",
    "HotspotsTab",
    "OverviewTab",
    "ReadinessOptionEntry",
    "ReadinessOptionsPayload",
    "ReadinessStrictEntry",
    "ReadinessTab",
    "RulePathEntry",
    "RunsTab",
    "SummaryData",
    "SummaryFileEntry",
    "SummaryFolderEntry",
    "SummaryRunEntry",
    "SummaryTabs",
]
