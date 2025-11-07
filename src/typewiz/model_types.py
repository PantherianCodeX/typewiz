from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from typing import TypedDict, cast


class Mode(StrEnum):
    CURRENT = "current"
    FULL = "full"

    @classmethod
    def from_str(cls, raw: str) -> Mode:
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"Unknown mode '{raw}'") from exc


class SeverityLevel(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    INFORMATION = "information"

    @classmethod
    def from_str(cls, raw: str) -> SeverityLevel:
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"Unknown severity '{raw}'") from exc

    @classmethod
    def coerce(cls, raw: object) -> SeverityLevel:
        if isinstance(raw, SeverityLevel):
            return raw
        if isinstance(raw, str):
            try:
                return cls.from_str(raw)
            except ValueError:
                return cls.INFORMATION
        return cls.INFORMATION


class ReadinessStatus(StrEnum):
    READY = "ready"
    CLOSE = "close"
    BLOCKED = "blocked"

    @classmethod
    def from_str(cls, raw: str) -> ReadinessStatus:
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"Unknown readiness status '{raw}'") from exc


class LogFormat(StrEnum):
    TEXT = "text"
    JSON = "json"

    @classmethod
    def from_str(cls, raw: str) -> LogFormat:
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"Unknown log format '{raw}'") from exc


class LicenseMode(StrEnum):
    COMMERCIAL = "commercial"
    EVALUATION = "evaluation"

    @classmethod
    def from_str(cls, raw: str) -> LicenseMode:
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"Unknown license mode '{raw}'") from exc


class DataFormat(StrEnum):
    JSON = "json"
    TABLE = "table"

    @classmethod
    def from_str(cls, raw: str) -> DataFormat:
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"Unknown data format '{raw}'") from exc


class DashboardView(StrEnum):
    OVERVIEW = "overview"
    ENGINES = "engines"
    HOTSPOTS = "hotspots"
    READINESS = "readiness"
    RUNS = "runs"

    @classmethod
    def from_str(cls, raw: str) -> DashboardView:
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"Unknown dashboard view '{raw}'") from exc


class ReadinessLevel(StrEnum):
    FOLDER = "folder"
    FILE = "file"

    @classmethod
    def from_str(cls, raw: str) -> ReadinessLevel:
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"Unknown readiness level '{raw}'") from exc


class HotspotKind(StrEnum):
    FILES = "files"
    FOLDERS = "folders"

    @classmethod
    def from_str(cls, raw: str) -> HotspotKind:
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"Unknown hotspot kind '{raw}'") from exc


class SummaryStyle(StrEnum):
    COMPACT = "compact"
    EXPANDED = "expanded"
    FULL = "full"

    @classmethod
    def from_str(cls, raw: str) -> SummaryStyle:
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"Unknown summary style '{raw}'") from exc


class SignaturePolicy(StrEnum):
    FAIL = "fail"
    WARN = "warn"
    IGNORE = "ignore"

    @classmethod
    def from_str(cls, raw: str) -> SignaturePolicy:
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"Unknown signature policy '{raw}'") from exc


class FailOnPolicy(StrEnum):
    NEVER = "never"
    NONE = "none"
    WARNINGS = "warnings"
    ERRORS = "errors"
    ANY = "any"

    @classmethod
    def from_str(cls, raw: str) -> FailOnPolicy:
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"Unknown fail-on policy '{raw}'") from exc


type CategoryMapping = dict[str, list[str]]


class OverrideEntry(TypedDict, total=False):
    path: str
    profile: str
    pluginArgs: list[str]
    include: list[str]
    exclude: list[str]


class DiagnosticPayload(TypedDict, total=False):
    tool: str
    severity: str
    path: str
    line: int
    column: int
    code: str | None
    message: str
    raw: dict[str, object]


class FileHashPayload(TypedDict, total=False):
    hash: str
    mtime: int
    size: int
    missing: bool
    unreadable: bool


def clone_override_entries(entries: Sequence[OverrideEntry]) -> list[OverrideEntry]:
    return [cast(OverrideEntry, dict(entry)) for entry in entries]
