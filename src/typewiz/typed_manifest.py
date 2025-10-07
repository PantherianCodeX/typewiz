from __future__ import annotations

from typing import Dict, List, TypedDict


class FileDiagnostic(TypedDict):
    line: int
    column: int
    severity: str
    code: str | None
    message: str


class FileEntry(TypedDict):
    path: str
    errors: int
    warnings: int
    information: int
    diagnostics: List[FileDiagnostic]


class FolderEntryRequired(TypedDict):
    path: str
    depth: int
    errors: int
    warnings: int
    information: int
    codeCounts: Dict[str, int]
    recommendations: List[str]


class FolderEntry(FolderEntryRequired, total=False):
    categoryCounts: Dict[str, int]


class RunSummary(TypedDict, total=False):
    errors: int
    warnings: int
    information: int
    total: int
    severityBreakdown: Dict[str, int]
    ruleCounts: Dict[str, int]
    categoryCounts: Dict[str, int]


class EngineOptionsEntry(TypedDict, total=False):
    profile: str | None
    configFile: str | None
    pluginArgs: List[str]
    include: List[str]
    exclude: List[str]
    overrides: List[Dict[str, object]]
    categoryMapping: Dict[str, List[str]]


class RunPayload(TypedDict):
    tool: str
    mode: str
    command: List[str]
    exitCode: int
    durationMs: float
    summary: RunSummary
    perFile: List[FileEntry]
    perFolder: List[FolderEntry]
    engineOptions: EngineOptionsEntry


class ManifestData(TypedDict):
    generatedAt: str
    projectRoot: str
    runs: List[RunPayload]


class AggregatedData(TypedDict):
    summary: RunSummary
    perFile: List[FileEntry]
    perFolder: List[FolderEntry]
