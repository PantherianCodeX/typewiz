# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

from typing import TypedDict

from .model_types import ReadinessStatus
from .typed_manifest import EngineOptionsEntry, ToolSummary


class SummaryRunEntry(TypedDict, total=False):
    command: list[str]
    errors: int
    warnings: int
    information: int
    total: int
    severityBreakdown: dict[str, int]
    ruleCounts: dict[str, int]
    categoryCounts: dict[str, int]
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


class OverviewTab(TypedDict):
    severityTotals: dict[str, int]
    categoryTotals: dict[str, int]
    runSummary: dict[str, SummaryRunEntry]


class EnginesTab(TypedDict):
    runSummary: dict[str, SummaryRunEntry]


class HotspotsTab(TypedDict):
    topRules: dict[str, int]
    topFolders: list[SummaryFolderEntry]
    topFiles: list[SummaryFileEntry]


class ReadinessStrictEntry(TypedDict, total=False):
    path: str
    diagnostics: int
    notes: list[str]
    recommendations: list[str]
    errors: int
    warnings: int
    information: int
    categories: dict[str, int]
    categoryStatus: dict[str, ReadinessStatus]


class ReadinessOptionsBucket(TypedDict, total=False):
    ready: list[ReadinessOptionEntry]
    close: list[ReadinessOptionEntry]
    blocked: list[ReadinessOptionEntry]
    threshold: int


class ReadinessTab(TypedDict, total=False):
    strict: dict[str, list[ReadinessStrictEntry]]
    options: dict[str, ReadinessOptionsBucket]


class ReadinessOptionEntry(TypedDict, total=False):
    path: str
    count: int
    errors: int
    warnings: int


class RunsTab(TypedDict):
    runSummary: dict[str, SummaryRunEntry]


class SummaryTabs(TypedDict):
    overview: OverviewTab
    engines: EnginesTab
    hotspots: HotspotsTab
    readiness: ReadinessTab
    runs: RunsTab


class SummaryData(TypedDict):
    generatedAt: object
    projectRoot: object
    runSummary: dict[str, SummaryRunEntry]
    severityTotals: dict[str, int]
    categoryTotals: dict[str, int]
    topRules: dict[str, int]
    topFolders: list[SummaryFolderEntry]
    topFiles: list[SummaryFileEntry]
    tabs: SummaryTabs
