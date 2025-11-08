from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from typing import Final, TypedDict, cast

from typewiz.runtime import JSONValue

from .type_aliases import CategoryKey, RelPath


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
            token = raw.strip().lower()
            if token.endswith("s"):
                singular = token[:-1]
                if singular in cls._value2member_map_:
                    token = singular
            if token == "info":
                token = "information"
            try:
                return cls.from_str(token)
            except ValueError:
                return cls.INFORMATION
        return cls.INFORMATION


DEFAULT_SEVERITIES: Final[tuple[SeverityLevel, SeverityLevel]] = (
    SeverityLevel.ERROR,
    SeverityLevel.WARNING,
)


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


class LogComponent(StrEnum):
    ENGINE = "engine"
    CLI = "cli"
    DASHBOARD = "dashboard"
    CACHE = "cache"

    @classmethod
    def from_str(cls, raw: str) -> LogComponent:
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"Unknown log component '{raw}'") from exc


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


class DashboardFormat(StrEnum):
    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"

    @classmethod
    def from_str(cls, raw: str) -> DashboardFormat:
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"Unknown dashboard format '{raw}'") from exc


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


class SummaryField(StrEnum):
    PROFILE = "profile"
    CONFIG = "config"
    PLUGIN_ARGS = "plugin-args"
    PATHS = "paths"
    OVERRIDES = "overrides"

    @classmethod
    def from_str(cls, raw: str) -> SummaryField:
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"Unknown summary field '{raw}'") from exc


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


class RatchetAction(StrEnum):
    INIT = "init"
    CHECK = "check"
    UPDATE = "update"
    REBASELINE_SIGNATURE = "rebaseline-signature"
    INFO = "info"

    @classmethod
    def from_str(cls, raw: str) -> RatchetAction:
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"Unknown ratchet action '{raw}'") from exc


class ManifestAction(StrEnum):
    VALIDATE = "validate"
    SCHEMA = "schema"

    @classmethod
    def from_str(cls, raw: str) -> ManifestAction:
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"Unknown manifest action '{raw}'") from exc


class QuerySection(StrEnum):
    OVERVIEW = "overview"
    HOTSPOTS = "hotspots"
    READINESS = "readiness"
    RUNS = "runs"
    ENGINES = "engines"
    RULES = "rules"

    @classmethod
    def from_str(cls, raw: str) -> QuerySection:
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"Unknown query section '{raw}'") from exc


class SummaryTabName(StrEnum):
    OVERVIEW = "overview"
    ENGINES = "engines"
    HOTSPOTS = "hotspots"
    READINESS = "readiness"
    RUNS = "runs"

    @classmethod
    def from_str(cls, raw: str) -> SummaryTabName:
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            raise ValueError(f"Unknown summary tab '{raw}'") from exc


class RecommendationCode(StrEnum):
    STRICT_READY = "strict-ready"
    CANDIDATE_ENABLE_UNKNOWN_CHECKS = "candidate-enable-unknown-checks"
    CANDIDATE_ENABLE_OPTIONAL_CHECKS = "candidate-enable-optional-checks"


type CategoryMapping = dict[CategoryKey, list[str]]


class OverrideEntry(TypedDict, total=False):
    path: str
    profile: str
    pluginArgs: list[str]
    include: list[RelPath]
    exclude: list[RelPath]


class DiagnosticPayload(TypedDict, total=False):
    tool: str
    severity: str
    path: str
    line: int
    column: int
    code: str | None
    message: str
    raw: dict[str, JSONValue]


class FileHashPayload(TypedDict, total=False):
    hash: str
    mtime: int
    size: int
    missing: bool
    unreadable: bool


def clone_override_entries(entries: Sequence[OverrideEntry]) -> list[OverrideEntry]:
    return [cast(OverrideEntry, dict(entry)) for entry in entries]
