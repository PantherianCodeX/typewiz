"""Pydantic models mirroring the manifest typed structures.

These models provide runtime validation and JSON Schema generation while staying
compatible with the existing ``typed_manifest`` TypedDict definitions.
"""

from __future__ import annotations

from typing import Any, cast

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .typed_manifest import ManifestData


class OverrideEntryModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    path: str | None = None
    profile: str | None = None
    pluginArgs: list[str] = Field(default_factory=list)
    include: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)


def _empty_override_list() -> list[OverrideEntryModel]:
    return []


class ToolSummaryModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    errors: int | None = None
    warnings: int | None = None
    information: int | None = None
    total: int | None = None


class FileDiagnosticModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    line: int
    column: int
    severity: str
    code: str | None = None
    message: str


class FileEntryModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    path: str
    errors: int
    warnings: int
    information: int
    diagnostics: list[FileDiagnosticModel]


class FolderEntryModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    path: str
    depth: int
    errors: int
    warnings: int
    information: int
    codeCounts: dict[str, int]
    recommendations: list[str]
    categoryCounts: dict[str, int] | None = None


class RunSummaryModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    errors: int | None = None
    warnings: int | None = None
    information: int | None = None
    total: int | None = None
    severityBreakdown: dict[str, int] | None = None
    ruleCounts: dict[str, int] | None = None
    categoryCounts: dict[str, int] | None = None


class EngineOptionsModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    profile: str | None = None
    configFile: str | None = None
    pluginArgs: list[str] = Field(default_factory=list)
    include: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)
    overrides: list[OverrideEntryModel] = Field(default_factory=_empty_override_list)
    categoryMapping: dict[str, list[str]] | None = None


class EngineErrorModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    message: str | None = None
    exitCode: int | None = None
    stderr: str | None = None


class RunPayloadModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    tool: str
    mode: str
    command: list[str]
    exitCode: int
    durationMs: float
    summary: RunSummaryModel
    perFile: list[FileEntryModel]
    perFolder: list[FolderEntryModel]
    engineOptions: EngineOptionsModel
    toolSummary: ToolSummaryModel | None = None
    engineArgsEffective: list[str] | None = None
    scannedPathsResolved: list[str] | None = None
    engineError: EngineErrorModel | None = None


def _empty_run_payload_list() -> list[RunPayloadModel]:
    return []


class ManifestModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    generatedAt: str | None = None
    projectRoot: str | None = None
    schemaVersion: str | None = None
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
        model = ManifestModel.model_validate(payload)
    except ValidationError as exc:
        raise ManifestValidationError(exc) from exc
    return manifest_from_model(model)


def manifest_json_schema() -> dict[str, Any]:
    """Return the canonical JSON Schema for typing audit manifests."""

    return ManifestModel.model_json_schema()


__all__ = [
    "ManifestModel",
    "ManifestValidationError",
    "manifest_from_model",
    "manifest_json_schema",
    "manifest_to_model",
    "validate_manifest_payload",
]
