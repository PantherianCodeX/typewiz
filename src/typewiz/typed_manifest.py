# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

from typing import TypedDict

from .model_types import CategoryMapping, Mode, OverrideEntry, SeverityLevel
from .type_aliases import CategoryKey, Command, RelPath


class FileDiagnostic(TypedDict):
    line: int
    column: int
    severity: SeverityLevel
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
    categoryCounts: dict[CategoryKey, int]


class RunSummary(TypedDict, total=False):
    errors: int
    warnings: int
    information: int
    total: int
    severityBreakdown: dict[SeverityLevel, int]
    ruleCounts: dict[str, int]
    categoryCounts: dict[CategoryKey, int]


class EngineOptionsEntry(TypedDict, total=False):
    profile: str | None
    configFile: str | None
    pluginArgs: list[str]
    include: list[RelPath]
    exclude: list[RelPath]
    overrides: list[OverrideEntry]
    categoryMapping: CategoryMapping


class ToolSummary(TypedDict, total=False):
    errors: int
    warnings: int
    information: int
    total: int


class RunPayloadRequired(TypedDict):
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
    toolSummary: ToolSummary
    engineArgsEffective: list[str]
    scannedPathsResolved: list[RelPath]
    engineError: EngineError


class EngineError(TypedDict, total=False):
    message: str
    exitCode: int
    stderr: str


class ManifestData(TypedDict, total=False):
    # Manifest metadata
    generatedAt: str
    projectRoot: str
    schemaVersion: str
    toolVersions: dict[str, str]
    fingerprintTruncated: bool
    # Collected runs
    runs: list[RunPayload]


class AggregatedData(TypedDict):
    summary: RunSummary
    perFile: list[FileEntry]
    perFolder: list[FolderEntry]
