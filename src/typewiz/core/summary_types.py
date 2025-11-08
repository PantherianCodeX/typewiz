# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

from typing import TypedDict

from ..typed_manifest import EngineOptionsEntry, ToolSummary
from .model_types import ReadinessStatus, SeverityLevel
from .type_aliases import CategoryKey, CategoryName, Command, RunId

CountsBySeverity = dict[SeverityLevel, int]
CountsByRule = dict[str, int]
CountsByCategory = dict[CategoryKey, int]


class SummaryRunEntry(TypedDict, total=False):
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
    path: str
    errors: int
    warnings: int
    information: int
    participatingRuns: int
    codeCounts: dict[str, int]
    recommendations: list[str]


class SummaryFileEntry(TypedDict):
    path: str
    errors: int
    warnings: int
    information: int


class RulePathEntry(TypedDict):
    path: str
    count: int


class OverviewTab(TypedDict):
    severityTotals: CountsBySeverity
    categoryTotals: CountsByCategory
    runSummary: dict[RunId, SummaryRunEntry]


class EnginesTab(TypedDict):
    runSummary: dict[RunId, SummaryRunEntry]


class HotspotsTab(TypedDict):
    topRules: dict[str, int]
    topFolders: list[SummaryFolderEntry]
    topFiles: list[SummaryFileEntry]
    ruleFiles: dict[str, list[RulePathEntry]]


class ReadinessStrictEntry(TypedDict, total=False):
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
    path: str
    count: int
    errors: int
    warnings: int


class ReadinessOptionsPayload(TypedDict):
    threshold: int
    buckets: dict[ReadinessStatus, tuple[ReadinessOptionEntry, ...]]


class ReadinessTab(TypedDict, total=False):
    strict: dict[ReadinessStatus, list[ReadinessStrictEntry]]
    options: dict[CategoryKey, ReadinessOptionsPayload]


class RunsTab(TypedDict):
    runSummary: dict[RunId, SummaryRunEntry]


class SummaryTabs(TypedDict):
    overview: OverviewTab
    engines: EnginesTab
    hotspots: HotspotsTab
    readiness: ReadinessTab
    runs: RunsTab


class SummaryData(TypedDict):
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
