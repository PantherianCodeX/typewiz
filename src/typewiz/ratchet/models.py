# Copyright (c) 2024 PantherianCodeX
"""Pydantic models describing ratchet budget files."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, ClassVar, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

RATCHET_SCHEMA_VERSION = 1


def normalise_severity(name: str) -> str:
    """Normalise severity names to lowercase tokens."""

    token = name.strip().lower()
    if token == "errors":
        return "error"
    if token == "warnings":
        return "warning"
    return token


class RatchetPathBudgetModel(BaseModel):
    """Per-path severity budgets."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    severities: dict[str, int] = Field(default_factory=dict)

    @field_validator("severities", mode="before")
    @classmethod
    def _coerce_map(cls, value: object) -> dict[str, int]:
        if not isinstance(value, Mapping):
            return {}
        mapping_value = cast(Mapping[object, object], value)
        result: dict[str, int] = {}
        for raw_key, raw_val in mapping_value.items():
            key = normalise_severity(str(raw_key))
            try:
                budget = int(cast(Any, raw_val))
            except (TypeError, ValueError):
                continue
            result[key] = max(budget, 0)
        return result


class RatchetRunBudgetModel(BaseModel):
    """Budgets for a specific tool/mode combination."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    severities: list[str]
    paths: dict[str, RatchetPathBudgetModel] = Field(default_factory=dict)
    targets: dict[str, int] = Field(default_factory=dict)
    engine_signature: dict[str, Any] = Field(default_factory=dict)

    @field_validator("severities", mode="before")
    @classmethod
    def _normalise_severities(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            tokens = [part.strip() for part in value.split(",") if part.strip()]
        elif isinstance(value, Sequence):
            sequence_value = cast(Sequence[object], value)
            tokens = [str(item).strip() for item in sequence_value if str(item).strip()]
        else:
            tokens = []
        return sorted({normalise_severity(token) for token in tokens})

    @field_validator("targets", mode="before")
    @classmethod
    def _coerce_targets(cls, value: object) -> dict[str, int]:
        if not isinstance(value, Mapping):
            return {}
        mapping_value = cast(Mapping[object, object], value)
        result: dict[str, int] = {}
        for raw_key, raw_val in mapping_value.items():
            key = normalise_severity(str(raw_key))
            try:
                budget = int(cast(Any, raw_val))
            except (TypeError, ValueError):
                continue
            result[key] = max(budget, 0)
        return result

    @model_validator(mode="after")
    def _apply_defaults(self) -> RatchetRunBudgetModel:
        severities = {normalise_severity(name) for name in self.severities}
        self.severities = sorted(severities)
        original_paths = cast(Mapping[str, object], self.paths)
        self.paths = {
            path: budget
            if isinstance(budget, RatchetPathBudgetModel)
            else RatchetPathBudgetModel.model_validate(budget)
            for path, budget in original_paths.items()
        }
        return self


class RatchetModel(BaseModel):
    """Root ratchet file."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    schema_version: int = Field(default=RATCHET_SCHEMA_VERSION, alias="schemaVersion")
    generated_at: str = Field(alias="generatedAt")
    manifest_path: Path | None = Field(default=None, alias="manifestPath")
    project_root: Path | None = Field(default=None, alias="projectRoot")
    runs: dict[str, RatchetRunBudgetModel] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _normalise(self) -> RatchetModel:
        original_runs = cast(Mapping[str, object], self.runs)
        self.runs = {
            key: budget
            if isinstance(budget, RatchetRunBudgetModel)
            else RatchetRunBudgetModel.model_validate(budget)
            for key, budget in sorted(original_runs.items())
        }
        return self


__all__ = [
    "RATCHET_SCHEMA_VERSION",
    "RatchetModel",
    "RatchetPathBudgetModel",
    "RatchetRunBudgetModel",
    "normalise_severity",
]
