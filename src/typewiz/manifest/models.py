# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Pydantic models mirroring the manifest typed structures.

These models provide runtime validation and JSON Schema generation while staying
compatible with the existing ``manifest.typed`` TypedDict definitions.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Annotated, Any, ClassVar, cast

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, ValidationError
from pydantic_core import PydanticCustomError

from .versioning import (
    CURRENT_MANIFEST_VERSION,
    InvalidManifestRunsError,
    InvalidManifestVersionTypeError,
    ManifestVersion,
    ManifestVersionError,
    UnsupportedManifestVersionError,
    ensure_current_manifest_version,
)

if TYPE_CHECKING:
    from typewiz.core.model_types import Mode, SeverityLevel
    from typewiz.core.type_aliases import CategoryKey, Command, RelPath
    from typewiz.runtime import JSONValue

    from .typed import ManifestData

STRICT_MODEL_CONFIG: ConfigDict = ConfigDict(extra="forbid", populate_by_name=True)


def alias_field(
    camel_name: str,
    *,
    default: object = ...,
    default_factory: Callable[[], object] | None = None,
) -> Any:  # noqa: ANN401 # JUSTIFIED: Must return Any to work with Pydantic field annotations
    """Return a Field configured with matching validation and serialization aliases.

    Args:
        camel_name: Canonical camelCase field name in the manifest schema.
        default: Default value for the field (use ... for required fields).
        default_factory: Factory function to generate default values.

    Returns:
        FieldInfo configured to deserialize/serialize the camelCase name while
        exposing a snake_case attribute on the model.

    Note:
        Returns Any to satisfy mypy's expectation for Pydantic Field usage in class
        annotations. At runtime, this returns a FieldInfo instance.
    """
    aliases = AliasChoices(camel_name)
    if default_factory is not None:
        return Field(
            default_factory=default_factory,
            validation_alias=aliases,
            serialization_alias=camel_name,
        )
    return Field(
        default=default,
        validation_alias=aliases,
        serialization_alias=camel_name,
    )


def _empty_relpath_list() -> list[RelPath]:
    """Create default empty list for RelPath values.

    Returns:
        Empty list for relative paths.
    """
    return []


class OverrideEntryModel(BaseModel):
    """Pydantic model for engine configuration overrides.

    Represents path-specific or profile-specific configuration overrides
    for type checking engines.

    Attributes:
        path: Optional path pattern for this override.
        profile: Optional profile name for this override.
        pluginArgs: List of additional arguments for the engine.
        include: List of paths to include in this override.
        exclude: List of paths to exclude from this override.
    """

    model_config: ClassVar[ConfigDict] = STRICT_MODEL_CONFIG

    path: str | None = None
    profile: str | None = None
    plugin_args: list[str] = alias_field("pluginArgs", default_factory=list)
    include: Annotated[list[RelPath], Field(default_factory=_empty_relpath_list)]
    exclude: Annotated[list[RelPath], Field(default_factory=_empty_relpath_list)]


def _empty_override_list() -> list[OverrideEntryModel]:
    """Create default empty list for override entries.

    Returns:
        Empty list of OverrideEntryModel objects.
    """
    return []


class ToolSummaryModel(BaseModel):
    """Pydantic model for tool-reported summary statistics.

    Contains the summary counts as reported directly by the type checking tool,
    which may differ from TypeWiz's aggregated counts.

    Attributes:
        errors: Count of errors reported by the tool.
        warnings: Count of warnings reported by the tool.
        information: Count of informational messages reported by the tool.
        total: Total count of diagnostics reported by the tool.
    """

    model_config: ClassVar[ConfigDict] = STRICT_MODEL_CONFIG

    errors: int | None = None
    warnings: int | None = None
    information: int | None = None
    total: int | None = None


class FileDiagnosticModel(BaseModel):
    """Pydantic model for a single diagnostic within a file.

    Attributes:
        line: Line number where the diagnostic occurs (1-indexed).
        column: Column number where the diagnostic occurs (1-indexed).
        severity: Severity level (error, warning, or information).
        code: Optional diagnostic code (e.g., "attr-defined").
        message: Human-readable diagnostic message.
    """

    model_config: ClassVar[ConfigDict] = STRICT_MODEL_CONFIG

    line: int
    column: int
    severity: SeverityLevel
    code: str | None = None
    message: str


class FileEntryModel(BaseModel):
    """Pydantic model for file-level diagnostic summary.

    Attributes:
        path: Relative path to the file.
        errors: Count of error-level diagnostics.
        warnings: Count of warning-level diagnostics.
        information: Count of information-level diagnostics.
        diagnostics: List of individual diagnostics in this file.
    """

    model_config: ClassVar[ConfigDict] = STRICT_MODEL_CONFIG

    path: str
    errors: int
    warnings: int
    information: int
    diagnostics: list[FileDiagnosticModel]


class FolderEntryModel(BaseModel):
    """Pydantic model for folder-level diagnostic aggregation.

    Attributes:
        path: Relative path to the folder.
        depth: Depth level in the folder hierarchy (1 = top level).
        errors: Count of error-level diagnostics in this folder.
        warnings: Count of warning-level diagnostics in this folder.
        information: Count of information-level diagnostics in this folder.
        codeCounts: Dictionary mapping diagnostic codes to counts.
        recommendations: List of recommendations for improving typing health.
        categoryCounts: Optional dictionary mapping categories to counts.
    """

    model_config: ClassVar[ConfigDict] = STRICT_MODEL_CONFIG

    path: str
    depth: int
    errors: int
    warnings: int
    information: int
    code_counts: dict[str, int] = alias_field("codeCounts", default=...)
    recommendations: list[str]
    category_counts: dict[CategoryKey, int] | None = alias_field("categoryCounts", default=None)


class RunSummaryModel(BaseModel):
    """Pydantic model for aggregated run summary statistics.

    Attributes:
        errors: Count of error-level diagnostics.
        warnings: Count of warning-level diagnostics.
        information: Count of information-level diagnostics.
        total: Total count of all diagnostics.
        severityBreakdown: Optional breakdown of counts by severity level.
        ruleCounts: Optional breakdown of counts by rule name.
        categoryCounts: Optional breakdown of counts by category.
    """

    model_config: ClassVar[ConfigDict] = STRICT_MODEL_CONFIG

    errors: int | None = None
    warnings: int | None = None
    information: int | None = None
    total: int | None = None
    severity_breakdown: dict[SeverityLevel, int] | None = alias_field("severityBreakdown", default=None)
    rule_counts: dict[str, int] | None = alias_field("ruleCounts", default=None)
    category_counts: dict[CategoryKey, int] | None = alias_field("categoryCounts", default=None)


class EngineOptionsModel(BaseModel):
    """Pydantic model for type checking engine configuration.

    Attributes:
        profile: Optional profile name (e.g., "strict", "standard").
        configFile: Optional path to the engine's config file.
        pluginArgs: List of additional command-line arguments.
        include: List of paths to include in type checking.
        exclude: List of paths to exclude from type checking.
        overrides: List of path or profile-specific overrides.
        categoryMapping: Optional mapping of categories to diagnostic code patterns.
    """

    model_config: ClassVar[ConfigDict] = STRICT_MODEL_CONFIG

    profile: str | None = None
    config_file: str | None = alias_field("configFile", default=None)
    plugin_args: list[str] = alias_field("pluginArgs", default_factory=list)
    include: Annotated[list[RelPath], Field(default_factory=_empty_relpath_list)]
    exclude: Annotated[list[RelPath], Field(default_factory=_empty_relpath_list)]
    overrides: list[OverrideEntryModel] = Field(default_factory=_empty_override_list)
    category_mapping: dict[CategoryKey, list[str]] | None = alias_field("categoryMapping", default=None)


class EngineErrorModel(BaseModel):
    """Pydantic model for engine execution errors.

    Attributes:
        message: Optional error message.
        exitCode: Optional exit code from the engine process.
        stderr: Optional stderr output from the engine.
    """

    model_config: ClassVar[ConfigDict] = STRICT_MODEL_CONFIG

    message: str | None = None
    exit_code: int | None = alias_field("exitCode", default=None)
    stderr: str | None = None


class RunPayloadModel(BaseModel):
    """Pydantic model for a complete type checking run.

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
        toolSummary: Optional summary as reported by the tool itself.
        engineArgsEffective: Optional list of effective engine arguments.
        scannedPathsResolved: Optional list of paths that were scanned.
        engineError: Optional error information if the engine failed.
    """

    model_config: ClassVar[ConfigDict] = STRICT_MODEL_CONFIG

    tool: str
    mode: Mode
    command: Command
    exit_code: int = alias_field("exitCode", default=...)
    duration_ms: float = alias_field("durationMs", default=...)
    summary: RunSummaryModel
    per_file: list[FileEntryModel] = alias_field("perFile", default=...)
    per_folder: list[FolderEntryModel] = alias_field("perFolder", default=...)
    engine_options: EngineOptionsModel = alias_field("engineOptions", default=...)
    tool_summary: ToolSummaryModel | None = alias_field("toolSummary", default=None)
    engine_args_effective: list[str] | None = alias_field("engineArgsEffective", default=None)
    scanned_paths_resolved: list[RelPath] | None = alias_field("scannedPathsResolved", default=None)
    engine_error: EngineErrorModel | None = alias_field("engineError", default=None)


def _empty_run_payload_list() -> list[RunPayloadModel]:
    """Create default empty list for run payloads.

    Returns:
        Empty list of RunPayloadModel objects.
    """
    return []


class ManifestModel(BaseModel):
    """Pydantic model for the top-level manifest structure.

    Attributes:
        generatedAt: ISO 8601 timestamp of manifest generation.
        projectRoot: Root directory of the project.
        schemaVersion: Manifest schema version (defaults to current version).
        fingerprintTruncated: Whether fingerprint data was truncated.
        toolVersions: Dictionary mapping tool names to version strings.
        runs: List of type checking runs included in this manifest.
    """

    model_config: ClassVar[ConfigDict] = STRICT_MODEL_CONFIG

    generated_at: str | None = alias_field("generatedAt", default=None)
    project_root: str | None = alias_field("projectRoot", default=None)
    schema_version: ManifestVersion = alias_field("schemaVersion", default=CURRENT_MANIFEST_VERSION)
    fingerprint_truncated: bool | None = alias_field("fingerprintTruncated", default=None)
    tool_versions: dict[str, str] | None = alias_field("toolVersions", default=None)
    runs: list[RunPayloadModel] = Field(default_factory=_empty_run_payload_list)


class ManifestValidationError(ValueError):
    """Validation error for manifest payloads.

    Wraps Pydantic ValidationError to provide compatibility with callers
    expecting ValueError.

    Attributes:
        validation_error: The underlying Pydantic ValidationError.
    """

    def __init__(self, validation_error: ValidationError) -> None:
        """Initialize with a Pydantic ValidationError.

        Args:
            validation_error: The Pydantic validation error to wrap.
        """
        super().__init__(str(validation_error))
        self.validation_error = validation_error


def manifest_from_model(model: ManifestModel) -> ManifestData:
    """Convert a validated Pydantic model into the typed manifest structure.

    Args:
        model: ManifestModel instance to convert.

    Returns:
        ManifestData TypedDict with the model's data.
    """
    data = model.model_dump(mode="python", exclude_none=True, by_alias=True)
    return cast("ManifestData", data)


def manifest_to_model(manifest: ManifestData) -> ManifestModel:
    """Convert a ManifestData TypedDict into a Pydantic model.

    Args:
        manifest: ManifestData TypedDict to convert.

    Returns:
        ManifestModel instance validated from the data.
    """
    return ManifestModel.model_validate(manifest)


def validate_manifest_payload(payload: JSONValue | ManifestData) -> ManifestData:
    """Validate an arbitrary manifest payload using ManifestModel.

    Performs schema version validation before validating the payload structure.
    Converts version-related errors into appropriate Pydantic validation errors.

    Args:
        payload: Arbitrary data (or a pre-typed ManifestData instance) to
            validate as a manifest.

    Returns:
        Validated ManifestData TypedDict.

    Raises:
        ManifestValidationError: If the payload fails validation or has version errors.
    """
    try:
        if isinstance(payload, Mapping):
            _ = ensure_current_manifest_version(cast("Mapping[str, JSONValue]", payload))
        model = ManifestModel.model_validate(payload)
    except ManifestVersionError as exc:
        location: tuple[str, ...]
        if isinstance(exc, UnsupportedManifestVersionError):
            error = PydanticCustomError(
                "manifest.version.unsupported",
                "Unsupported manifest schema version: {version}",
                {"version": exc.version},
            )
            location = ("schemaVersion",)
        elif isinstance(exc, InvalidManifestVersionTypeError):
            error = PydanticCustomError(
                "manifest.version.type",
                "Unsupported schemaVersion type: {type}",
                {"type": type(exc.value).__name__},
            )
            location = ("schemaVersion",)
        elif isinstance(exc, InvalidManifestRunsError):
            error = PydanticCustomError(
                "manifest.runs.type",
                "runs must be a list of run payloads",
                {},
            )
            location = ("runs",)
        else:
            error = PydanticCustomError(
                "manifest.version",
                "Manifest schema version error: {message}",
                {"message": str(exc)},
            )
            location = ("schemaVersion",)
        validation_error = ValidationError.from_exception_data(
            ManifestModel.__name__,
            [
                {
                    "type": error,
                    "loc": location,
                    "input": payload,
                },
            ],
        )
        raise ManifestValidationError(validation_error) from exc
    except ValidationError as exc:
        raise ManifestValidationError(exc) from exc
    return manifest_from_model(model)


def manifest_json_schema() -> dict[str, Any]:
    """Return the canonical JSON Schema for typing audit manifests.

    Generates a JSON Schema from the ManifestModel and adds standard
    schema metadata fields.

    Returns:
        Dictionary containing the complete JSON Schema definition.
    """
    schema = ManifestModel.model_json_schema(by_alias=True)
    schema["$schema"] = "https://json-schema.org/draft-07/schema#"
    schema.setdefault("$id", "https://typewiz.dev/schema/manifest.json")
    schema.setdefault("additionalProperties", False)
    return schema


__all__ = [
    "ManifestModel",
    "ManifestValidationError",
    "manifest_from_model",
    "manifest_json_schema",
    "manifest_to_model",
    "validate_manifest_payload",
]
