from __future__ import annotations

from typing import TypedDict


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
    diagnostics: list[FileDiagnostic]


class FolderEntryRequired(TypedDict):
    path: str
    depth: int
    errors: int
    warnings: int
    information: int
    codeCounts: dict[str, int]
    recommendations: list[str]


class FolderEntry(FolderEntryRequired, total=False):
    categoryCounts: dict[str, int]


class RunSummary(TypedDict, total=False):
    errors: int
    warnings: int
    information: int
    total: int
    severityBreakdown: dict[str, int]
    ruleCounts: dict[str, int]
    categoryCounts: dict[str, int]


class EngineOptionsEntry(TypedDict, total=False):
    profile: str | None
    configFile: str | None
    pluginArgs: list[str]
    include: list[str]
    exclude: list[str]
    overrides: list[dict[str, object]]
    categoryMapping: dict[str, list[str]]


class ToolSummary(TypedDict, total=False):
    errors: int
    warnings: int
    information: int
    total: int


class RunPayloadRequired(TypedDict):
    tool: str
    mode: str
    command: list[str]
    exitCode: int
    durationMs: float
    summary: RunSummary
    perFile: list[FileEntry]
    perFolder: list[FolderEntry]
    engineOptions: EngineOptionsEntry


class RunPayload(RunPayloadRequired, total=False):
    toolSummary: ToolSummary


class ManifestData(TypedDict):
    generatedAt: str
    projectRoot: str
    runs: list[RunPayload]


class AggregatedData(TypedDict):
    summary: RunSummary
    perFile: list[FileEntry]
    perFolder: list[FolderEntry]
