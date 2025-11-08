# Copyright (c) 2024 PantherianCodeX

"""Pydantic models mirroring the manifest typed structures.

These models provide runtime validation and JSON Schema generation while staying
compatible with the existing ``typed_manifest`` TypedDict definitions.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, Any, ClassVar, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic_core import PydanticCustomError

from .core.model_types import Mode, SeverityLevel
from .core.type_aliases import CategoryKey, Command, RelPath
from .manifest_versioning import (
    CURRENT_MANIFEST_VERSION,
    InvalidManifestRunsError,
    InvalidManifestVersionTypeError,
    ManifestVersion,
    ManifestVersionError,
    UnsupportedManifestVersionError,
    ensure_current_manifest_version,
)
from .typed_manifest import ManifestData

STRICT_MODEL_CONFIG: ConfigDict = ConfigDict(extra="forbid")


def _empty_relpath_list() -> list[RelPath]:
    return []


class OverrideEntryModel(BaseModel):
    model_config: ClassVar[ConfigDict] = STRICT_MODEL_CONFIG

    path: str | None = None
    profile: str | None = None
    pluginArgs: list[str] = Field(default_factory=list)
    include: Annotated[list[RelPath], Field(default_factory=_empty_relpath_list)]
    exclude: Annotated[list[RelPath], Field(default_factory=_empty_relpath_list)]


def _empty_override_list() -> list[OverrideEntryModel]:
    return []


class ToolSummaryModel(BaseModel):
    model_config: ClassVar[ConfigDict] = STRICT_MODEL_CONFIG

    errors: int | None = None
    warnings: int | None = None
    information: int | None = None
    total: int | None = None


class FileDiagnosticModel(BaseModel):
    model_config: ClassVar[ConfigDict] = STRICT_MODEL_CONFIG

    line: int
    column: int
    severity: SeverityLevel
    code: str | None = None
    message: str


class FileEntryModel(BaseModel):
    model_config: ClassVar[ConfigDict] = STRICT_MODEL_CONFIG

    path: str
    errors: int
    warnings: int
    information: int
    diagnostics: list[FileDiagnosticModel]


class FolderEntryModel(BaseModel):
    model_config: ClassVar[ConfigDict] = STRICT_MODEL_CONFIG

    path: str
    depth: int
    errors: int
    warnings: int
    information: int
    codeCounts: dict[str, int]
    recommendations: list[str]
    categoryCounts: dict[CategoryKey, int] | None = None


class RunSummaryModel(BaseModel):
    model_config: ClassVar[ConfigDict] = STRICT_MODEL_CONFIG

    errors: int | None = None
    warnings: int | None = None
    information: int | None = None
    total: int | None = None
    severityBreakdown: dict[SeverityLevel, int] | None = None
    ruleCounts: dict[str, int] | None = None
    categoryCounts: dict[CategoryKey, int] | None = None


class EngineOptionsModel(BaseModel):
    model_config: ClassVar[ConfigDict] = STRICT_MODEL_CONFIG

    profile: str | None = None
    configFile: str | None = None
    pluginArgs: list[str] = Field(default_factory=list)
    include: Annotated[list[RelPath], Field(default_factory=_empty_relpath_list)]
    exclude: Annotated[list[RelPath], Field(default_factory=_empty_relpath_list)]
    overrides: list[OverrideEntryModel] = Field(default_factory=_empty_override_list)
    categoryMapping: dict[CategoryKey, list[str]] | None = None


class EngineErrorModel(BaseModel):
    model_config: ClassVar[ConfigDict] = STRICT_MODEL_CONFIG

    message: str | None = None
    exitCode: int | None = None
    stderr: str | None = None


class RunPayloadModel(BaseModel):
    model_config: ClassVar[ConfigDict] = STRICT_MODEL_CONFIG

    tool: str
    mode: Mode
    command: Command
    exitCode: int
    durationMs: float
    summary: RunSummaryModel
    perFile: list[FileEntryModel]
    perFolder: list[FolderEntryModel]
    engineOptions: EngineOptionsModel
    toolSummary: ToolSummaryModel | None = None
    engineArgsEffective: list[str] | None = None
    scannedPathsResolved: list[RelPath] | None = None
    engineError: EngineErrorModel | None = None


def _empty_run_payload_list() -> list[RunPayloadModel]:
    return []


class ManifestModel(BaseModel):
    model_config: ClassVar[ConfigDict] = STRICT_MODEL_CONFIG

    generatedAt: str | None = None
    projectRoot: str | None = None
    schemaVersion: ManifestVersion = Field(default=CURRENT_MANIFEST_VERSION)
    fingerprintTruncated: bool | None = None
    toolVersions: dict[str, str] | None = None
    runs: list[RunPayloadModel] = Field(default_factory=_empty_run_payload_list)


class ManifestValidationError(ValueError):
    """Wrap Pydantic validation errors for callers that expect ValueError."""

    def __init__(self, validation_error: ValidationError) -> None:
        super().__init__(str(validation_error))
        self.validation_error = validation_error


def manifest_from_model(model: ManifestModel) -> ManifestData:
    """Convert a validated Pydantic model into the typed manifest structure."""

    data = model.model_dump(mode="python", exclude_none=True)
    return cast(ManifestData, data)


def manifest_to_model(manifest: ManifestData) -> ManifestModel:
    return ManifestModel.model_validate(manifest)


def validate_manifest_payload(payload: Any) -> ManifestData:
    """Validate an arbitrary manifest payload using ``ManifestModel``."""

    try:
        if isinstance(payload, Mapping):
            _ = ensure_current_manifest_version(cast(Mapping[str, Any], payload))
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
    """Return the canonical JSON Schema for typing audit manifests."""
    schema = ManifestModel.model_json_schema()
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
