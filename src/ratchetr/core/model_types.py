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

# ignore JUSTIFIED: StrEnum inheritance stack exceeds pylint threshold; review later
# pylint: disable=too-many-ancestors, useless-suppression  # noqa: FIX002,TD003  # TODO@PantherianCodeX: Revisit StrEnum ancestry once enum layering is simplified

"""Model types and enumerations for ratchetr.

This module defines core model types, enumerations, and TypedDict classes used
throughout ratchetr. It includes:

- Mode and severity enumerations for type checking runs
- Status enumerations for readiness and licensing
- Format enumerations for output and dashboard rendering
- Action enumerations for CLI commands
- TypedDict definitions for data payloads
- Utility functions for type coercion and validation
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final, TypeAlias, cast

from ratchetr.compat import StrEnum, TypedDict

from .type_aliases import CategoryKey, RelPath

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ratchetr.json import JSONValue


class Mode(StrEnum):
    """Execution scheduling modes.

    CURRENT: Scope precedence includes CLI positional args:
        1. CLI positional arguments (e.g., `rtr audit src/ tests/`)
        2. Environment variable (RATCHETR_INCLUDE)
        3. Config file (audit.default_include)
        4. Default: ["."]

    TARGET: Scope precedence excludes CLI positional args:
        1. Environment variable (RATCHETR_INCLUDE)
        2. Config file (audit.default_include)
        3. Default: ["."]

    When CURRENT and TARGET produce equivalent EnginePlans for an engine,
    only TARGET executes (TARGET is canonical for ratcheting eligibility).

    Note: "FULL" is reserved for future all-options-enabled mode supplied
    by plugins, where the plugin determines comprehensive analysis scope.

    Attributes:
        CURRENT: Check using scope that may include CLI-specified paths.
        TARGET: Check using environment/config/default scope only.
    """

    CURRENT = "current"
    TARGET = "target"

    @classmethod
    def from_str(cls, raw: str) -> Mode:
        """Create a Mode enum from a string value.

        Args:
            raw: String representation of the mode.

        Returns:
            Mode enum value.

        Raises:
            ValueError: If the string does not match any Mode value.
        """
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            msg = f"Unknown mode '{raw}'"
            raise ValueError(msg) from exc


class SeverityLevel(StrEnum):
    """Enumeration of diagnostic severity levels.

    Attributes:
        ERROR: Critical issues that prevent type safety.
        WARNING: Potential issues that should be addressed.
        INFORMATION: Informational diagnostics.
    """

    ERROR = "error"
    WARNING = "warning"
    INFORMATION = "information"

    @classmethod
    def from_str(cls, raw: str) -> SeverityLevel:
        """Create a SeverityLevel enum from a string value.

        Args:
            raw: String representation of the severity level.

        Returns:
            SeverityLevel enum value.

        Raises:
            ValueError: If the string does not match any SeverityLevel value.
        """
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            msg = f"Unknown severity '{raw}'"
            raise ValueError(msg) from exc

    @classmethod
    def coerce(cls, raw: object) -> SeverityLevel:
        """Coerce an arbitrary object to a SeverityLevel with fallback.

        Attempts to convert the input to a SeverityLevel, handling common
        variations like plural forms and 'info' shorthand. Returns
        INFORMATION as the default if coercion fails.

        Args:
            raw: Object to coerce to a SeverityLevel.

        Returns:
            SeverityLevel enum value, defaulting to INFORMATION.
        """
        if isinstance(raw, SeverityLevel):
            return raw
        if isinstance(raw, str):
            input_str = raw.strip().lower()
            if input_str.endswith("s"):
                singular = input_str[:-1]
                if singular in cls._value2member_map_:
                    input_str = singular
            if input_str == "info":
                input_str = "information"
            try:
                return cls.from_str(input_str)
            except ValueError:
                return cls.INFORMATION
        return cls.INFORMATION


DEFAULT_SEVERITIES: Final[tuple[SeverityLevel, SeverityLevel]] = (
    SeverityLevel.ERROR,
    SeverityLevel.WARNING,
)


class ReadinessStatus(StrEnum):
    """Enumeration of readiness status levels for type checking adoption.

    Attributes:
        READY: Module/file is ready for strict type checking.
        CLOSE: Module/file is close to ready with minimal issues.
        BLOCKED: Module/file has significant blocking issues.
    """

    READY = "ready"
    CLOSE = "close"
    BLOCKED = "blocked"

    @classmethod
    def from_str(cls, raw: str) -> ReadinessStatus:
        """Create a ReadinessStatus enum from a string value.

        Args:
            raw: String representation of the readiness status.

        Returns:
            ReadinessStatus enum value.

        Raises:
            ValueError: If the string does not match any ReadinessStatus value.
        """
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            msg = f"Unknown readiness status '{raw}'"
            raise ValueError(msg) from exc


class LogFormat(StrEnum):
    """Enumeration of log output formats.

    Attributes:
        TEXT: Human-readable text format.
        JSON: Machine-readable JSON format.
    """

    TEXT = "text"
    JSON = "json"

    @classmethod
    def from_str(cls, raw: str) -> LogFormat:
        """Create a LogFormat enum from a string value.

        Args:
            raw: String representation of the log format.

        Returns:
            LogFormat enum value.

        Raises:
            ValueError: If the string does not match any LogFormat value.
        """
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            msg = f"Unknown log format '{raw}'"
            raise ValueError(msg) from exc


class LogComponent(StrEnum):
    """Enumeration of loggable system components.

    Attributes:
        ENGINE: Type checking engine component.
        CLI: Command-line interface component.
        DASHBOARD: Dashboard rendering component.
        CACHE: Caching system component.
        RATCHET: Ratcheting mechanism component.
        SERVICES: Service layer component.
        MANIFEST: Manifest handling component.
    """

    ENGINE = "engine"
    CLI = "cli"
    DASHBOARD = "dashboard"
    CACHE = "cache"
    RATCHET = "ratchet"
    SERVICES = "services"
    MANIFEST = "manifest"

    @classmethod
    def from_str(cls, raw: str) -> LogComponent:
        """Create a LogComponent enum from a string value.

        Args:
            raw: String representation of the log component.

        Returns:
            LogComponent enum value.

        Raises:
            ValueError: If the string does not match any LogComponent value.
        """
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            msg = f"Unknown log component '{raw}'"
            raise ValueError(msg) from exc


class DataFormat(StrEnum):
    """Enumeration of data output formats.

    Attributes:
        JSON: JSON data format.
        TABLE: Tabular data format.
    """

    JSON = "json"
    TABLE = "table"

    @classmethod
    def from_str(cls, raw: str) -> DataFormat:
        """Create a DataFormat enum from a string value.

        Args:
            raw: String representation of the data format.

        Returns:
            DataFormat enum value.

        Raises:
            ValueError: If the string does not match any DataFormat value.
        """
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            msg = f"Unknown data format '{raw}'"
            raise ValueError(msg) from exc


class DashboardFormat(StrEnum):
    """Enumeration of dashboard rendering formats.

    Attributes:
        JSON: Raw JSON data format.
        MARKDOWN: Markdown documentation format.
        HTML: HTML webpage format.
    """

    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"

    @classmethod
    def from_str(cls, raw: str) -> DashboardFormat:
        """Create a DashboardFormat enum from a string value.

        Args:
            raw: String representation of the dashboard format.

        Returns:
            DashboardFormat enum value.

        Raises:
            ValueError: If the string does not match any DashboardFormat value.
        """
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            msg = f"Unknown dashboard format '{raw}'"
            raise ValueError(msg) from exc


class DashboardView(StrEnum):
    """Enumeration of dashboard view types.

    Attributes:
        OVERVIEW: High-level overview of type checking results.
        ENGINES: Engine-specific diagnostic information.
        HOTSPOTS: Areas with the most type checking issues.
        READINESS: Readiness analysis for strict type checking.
        RUNS: Individual run details and history.
    """

    OVERVIEW = "overview"
    ENGINES = "engines"
    HOTSPOTS = "hotspots"
    READINESS = "readiness"
    RUNS = "runs"

    @classmethod
    def from_str(cls, raw: str) -> DashboardView:
        """Create a DashboardView enum from a string value.

        Args:
            raw: String representation of the dashboard view.

        Returns:
            DashboardView enum value.

        Raises:
            ValueError: If the string does not match any DashboardView value.
        """
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            msg = f"Unknown dashboard view '{raw}'"
            raise ValueError(msg) from exc


class ReadinessLevel(StrEnum):
    """Enumeration of readiness analysis granularity levels.

    Attributes:
        FOLDER: Folder-level readiness analysis.
        FILE: File-level readiness analysis.
    """

    FOLDER = "folder"
    FILE = "file"

    @classmethod
    def from_str(cls, raw: str) -> ReadinessLevel:
        """Create a ReadinessLevel enum from a string value.

        Args:
            raw: String representation of the readiness level.

        Returns:
            ReadinessLevel enum value.

        Raises:
            ValueError: If the string does not match any ReadinessLevel value.
        """
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            msg = f"Unknown readiness level '{raw}'"
            raise ValueError(msg) from exc


class HotspotKind(StrEnum):
    """Enumeration of hotspot analysis types.

    Attributes:
        FILES: File-level hotspot analysis.
        FOLDERS: Folder-level hotspot analysis.
    """

    FILES = "files"
    FOLDERS = "folders"

    @classmethod
    def from_str(cls, raw: str) -> HotspotKind:
        """Create a HotspotKind enum from a string value.

        Args:
            raw: String representation of the hotspot kind.

        Returns:
            HotspotKind enum value.

        Raises:
            ValueError: If the string does not match any HotspotKind value.
        """
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            msg = f"Unknown hotspot kind '{raw}'"
            raise ValueError(msg) from exc


class SummaryStyle(StrEnum):
    """Enumeration of summary display styles.

    Attributes:
        COMPACT: Minimal summary output.
        EXPANDED: Detailed summary with additional context.
        FULL: Complete summary with all available information.
    """

    COMPACT = "compact"
    EXPANDED = "expanded"
    FULL = "full"

    @classmethod
    def from_str(cls, raw: str) -> SummaryStyle:
        """Create a SummaryStyle enum from a string value.

        Args:
            raw: String representation of the summary style.

        Returns:
            SummaryStyle enum value.

        Raises:
            ValueError: If the string does not match any SummaryStyle value.
        """
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            msg = f"Unknown summary style '{raw}'"
            raise ValueError(msg) from exc


class SummaryField(StrEnum):
    """Enumeration of summary field types.

    Attributes:
        PROFILE: Type checking profile configuration.
        CONFIG: Configuration file settings.
        PLUGIN_ARGS: Plugin-specific arguments.
        PATHS: Analyzed file paths.
        OVERRIDES: Path-specific override configurations.
    """

    PROFILE = "profile"
    CONFIG = "config"
    PLUGIN_ARGS = "plugin-args"
    PATHS = "paths"
    OVERRIDES = "overrides"

    @classmethod
    def from_str(cls, raw: str) -> SummaryField:
        """Create a SummaryField enum from a string value.

        Args:
            raw: String representation of the summary field.

        Returns:
            SummaryField enum value.

        Raises:
            ValueError: If the string does not match any SummaryField value.
        """
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            msg = f"Unknown summary field '{raw}'"
            raise ValueError(msg) from exc


class SignaturePolicy(StrEnum):
    """Enumeration of ratchet signature validation policies.

    Attributes:
        FAIL: Fail the build on signature mismatch.
        WARN: Warn on signature mismatch but don't fail.
        IGNORE: Ignore signature mismatches.
    """

    FAIL = "fail"
    WARN = "warn"
    IGNORE = "ignore"

    @classmethod
    def from_str(cls, raw: str) -> SignaturePolicy:
        """Create a SignaturePolicy enum from a string value.

        Args:
            raw: String representation of the signature policy.

        Returns:
            SignaturePolicy enum value.

        Raises:
            ValueError: If the string does not match any SignaturePolicy value.
        """
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            msg = f"Unknown signature policy '{raw}'"
            raise ValueError(msg) from exc


class FailOnPolicy(StrEnum):
    """Enumeration of failure policies for type checking runs.

    Attributes:
        NEVER: Never fail regardless of diagnostics.
        NONE: Fail only if no diagnostics are found.
        WARNINGS: Fail on warnings or errors.
        ERRORS: Fail only on errors.
        ANY: Fail on any diagnostic.
    """

    NEVER = "never"
    NONE = "none"
    WARNINGS = "warnings"
    ERRORS = "errors"
    ANY = "any"

    @classmethod
    def from_str(cls, raw: str) -> FailOnPolicy:
        """Create a FailOnPolicy enum from a string value.

        Args:
            raw: String representation of the fail-on policy.

        Returns:
            FailOnPolicy enum value.

        Raises:
            ValueError: If the string does not match any FailOnPolicy value.
        """
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            msg = f"Unknown fail-on policy '{raw}'"
            raise ValueError(msg) from exc


class RatchetAction(StrEnum):
    """Enumeration of ratchet command actions.

    Attributes:
        INIT: Initialize a new ratchet baseline.
        CHECK: Check current state against ratchet baseline.
        UPDATE: Update the ratchet baseline.
        REBASELINE_SIGNATURE: Rebaseline the signature without changing counts.
        INFO: Display ratchet information.
    """

    INIT = "init"
    CHECK = "check"
    UPDATE = "update"
    REBASELINE_SIGNATURE = "rebaseline-signature"
    INFO = "info"

    @classmethod
    def from_str(cls, raw: str) -> RatchetAction:
        """Create a RatchetAction enum from a string value.

        Args:
            raw: String representation of the ratchet action.

        Returns:
            RatchetAction enum value.

        Raises:
            ValueError: If the string does not match any RatchetAction value.
        """
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            msg = f"Unknown ratchet action '{raw}'"
            raise ValueError(msg) from exc


class ManifestAction(StrEnum):
    """Enumeration of manifest command actions.

    Attributes:
        VALIDATE: Validate a manifest file.
        SCHEMA: Display the manifest JSON schema.
    """

    VALIDATE = "validate"
    SCHEMA = "schema"

    @classmethod
    def from_str(cls, raw: str) -> ManifestAction:
        """Create a ManifestAction enum from a string value.

        Args:
            raw: String representation of the manifest action.

        Returns:
            ManifestAction enum value.

        Raises:
            ValueError: If the string does not match any ManifestAction value.
        """
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            msg = f"Unknown manifest action '{raw}'"
            raise ValueError(msg) from exc


class EngineErrorKind(StrEnum):
    """Enumeration of symbolic engine error categories.

    These kinds distinguish different failure modes during engine execution,
    enabling structured error handling and reporting.

    Attributes:
        ENGINE_OUTPUT_PARSE_FAILED: Engine ran but output couldn't be parsed.
        ENGINE_NO_PARSEABLE_OUTPUT: Engine produced no output to parse.
        ENGINE_TOOL_NOT_FOUND: Engine executable not found in PATH.
        ENGINE_CRASHED: Engine process crashed or was terminated.
        ENGINE_CONFIG_ERROR: Configuration error prevented execution.
    """

    ENGINE_OUTPUT_PARSE_FAILED = "engine-output-parse-failed"
    ENGINE_NO_PARSEABLE_OUTPUT = "engine-no-parseable-output"
    ENGINE_TOOL_NOT_FOUND = "engine-tool-not-found"
    ENGINE_CRASHED = "engine-crashed"
    ENGINE_CONFIG_ERROR = "engine-config-error"

    @classmethod
    def from_str(cls, raw: str) -> EngineErrorKind:
        """Create an EngineErrorKind enum from a string value.

        Args:
            raw: String representation of the error kind.

        Returns:
            EngineErrorKind enum value.

        Raises:
            ValueError: If the string does not match any EngineErrorKind value.
        """
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            msg = f"Unknown engine error kind '{raw}'"
            raise ValueError(msg) from exc


class QuerySection(StrEnum):
    """Enumeration of queryable dashboard sections.

    Attributes:
        OVERVIEW: Overview summary section.
        HOTSPOTS: Hotspot analysis section.
        READINESS: Readiness analysis section.
        RUNS: Individual runs section.
        ENGINES: Engine-specific section.
        RULES: Rule-specific analysis section.
    """

    OVERVIEW = "overview"
    HOTSPOTS = "hotspots"
    READINESS = "readiness"
    RUNS = "runs"
    ENGINES = "engines"
    RULES = "rules"

    @classmethod
    def from_str(cls, raw: str) -> QuerySection:
        """Create a QuerySection enum from a string value.

        Args:
            raw: String representation of the query section.

        Returns:
            QuerySection enum value.

        Raises:
            ValueError: If the string does not match any QuerySection value.
        """
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            msg = f"Unknown query section '{raw}'"
            raise ValueError(msg) from exc


class SummaryTabName(StrEnum):
    """Enumeration of summary tab names.

    Attributes:
        OVERVIEW: Overview tab.
        ENGINES: Engines tab.
        HOTSPOTS: Hotspots tab.
        READINESS: Readiness tab.
        RUNS: Runs tab.
    """

    OVERVIEW = "overview"
    ENGINES = "engines"
    HOTSPOTS = "hotspots"
    READINESS = "readiness"
    RUNS = "runs"

    @classmethod
    def from_str(cls, raw: str) -> SummaryTabName:
        """Create a SummaryTabName enum from a string value.

        Args:
            raw: String representation of the summary tab.

        Returns:
            SummaryTabName enum value.

        Raises:
            ValueError: If the string does not match any SummaryTabName value.
        """
        value = raw.strip().lower()
        try:
            return cls(value)
        except ValueError as exc:
            msg = f"Unknown summary tab '{raw}'"
            raise ValueError(msg) from exc


class RecommendationCode(StrEnum):
    """Enumeration of recommendation codes for type checking adoption.

    Attributes:
        STRICT_READY: Module is ready for strict type checking.
        CANDIDATE_ENABLE_UNKNOWN_CHECKS: Consider enabling unknown type checks.
        CANDIDATE_ENABLE_OPTIONAL_CHECKS: Consider enabling optional checks.
    """

    STRICT_READY = "strict-ready"
    CANDIDATE_ENABLE_UNKNOWN_CHECKS = "candidate-enable-unknown-checks"
    CANDIDATE_ENABLE_OPTIONAL_CHECKS = "candidate-enable-optional-checks"


CategoryMapping: TypeAlias = dict[CategoryKey, list[str]]


class OverrideEntry(TypedDict, total=False):
    """TypedDict for path-specific configuration overrides.

    Attributes:
        path: File or folder path to apply the override to.
        profile: Type checking profile to use for this path.
        pluginArgs: Additional plugin arguments for this path.
        include: Paths to include in type checking.
        exclude: Paths to exclude from type checking.
    """

    path: str
    profile: str
    pluginArgs: list[str]
    include: list[RelPath]
    exclude: list[RelPath]


class DiagnosticPayload(TypedDict, total=False):
    """TypedDict for diagnostic message data payloads.

    Attributes:
        tool: Name of the type checking tool that generated the diagnostic.
        severity: Severity level of the diagnostic.
        path: File path where the diagnostic was found.
        line: Line number of the diagnostic.
        column: Column number of the diagnostic.
        code: Diagnostic error code if available.
        message: Human-readable diagnostic message.
        raw: Raw diagnostic data from the tool.
    """

    tool: str
    severity: str
    path: str
    line: int
    column: int
    code: str | None
    message: str
    raw: dict[str, JSONValue]


class FileHashPayload(TypedDict, total=False):
    """TypedDict for file hash and metadata information.

    Attributes:
        hash: Content hash of the file.
        mtime: Modification timestamp of the file.
        size: Size of the file in bytes.
        missing: Whether the file is missing.
        unreadable: Whether the file is unreadable.
    """

    hash: str
    mtime: int
    size: int
    missing: bool
    unreadable: bool


def clone_override_entries(entries: Sequence[OverrideEntry]) -> list[OverrideEntry]:
    """Create a deep copy of override entries.

    Args:
        entries: Sequence of OverrideEntry dictionaries to clone.

    Returns:
        List of cloned OverrideEntry dictionaries.
    """
    return [cast("OverrideEntry", dict(entry)) for entry in entries]
