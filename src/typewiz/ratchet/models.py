# Copyright (c) 2024 PantherianCodeX
"""Pydantic models describing ratchet budget files."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, ClassVar, Final, TypedDict, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ..model_types import SeverityLevel
from ..typed_manifest import ModeStr
from ..utils import JSONValue

RATCHET_SCHEMA_VERSION: Final[int] = 1


def _new_severity_map() -> dict[SeverityLevel, int]:
    return {}


def _sorted_severity_list(values: Iterable[SeverityLevel]) -> list[SeverityLevel]:
    return sorted(values, key=lambda severity: severity.value)


def _parse_budget_value(raw: object) -> int:
    budget = int(cast(Any, raw))
    return max(budget, 0)


class RatchetPathBudgetModel(BaseModel):
    """Per-path severity budgets."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    severities: dict[SeverityLevel, int] = Field(default_factory=_new_severity_map)

    @field_validator("severities", mode="before")
    @classmethod
    def _coerce_map(cls, value: object) -> dict[SeverityLevel, int]:
        if not isinstance(value, Mapping):
            raise TypeError("severities must be a mapping")
        mapping_value = cast(Mapping[object, object], value)
        result: dict[SeverityLevel, int] = {}
        for raw_key, raw_val in mapping_value.items():
            severity = cls._parse_severity(raw_key)
            result[severity] = _parse_budget_value(raw_val)
        return result

    @staticmethod
    def _parse_severity(raw: object) -> SeverityLevel:
        if isinstance(raw, SeverityLevel):
            return raw
        return SeverityLevel.from_str(str(raw))


class RatchetRunBudgetModel(BaseModel):
    """Budgets for a specific tool/mode combination."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    severities: list[SeverityLevel]
    paths: dict[str, RatchetPathBudgetModel] = Field(default_factory=dict)
    targets: dict[SeverityLevel, int] = Field(default_factory=_new_severity_map)
    engine_signature: EngineSignaturePayloadWithHash | None = None

    @field_validator("severities", mode="before")
    @classmethod
    def _normalise_severities(cls, value: object) -> list[SeverityLevel]:
        if value is None:
            return []
        if isinstance(value, str):
            tokens_list: list[object] = [part.strip() for part in value.split(",") if part.strip()]
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            tokens_list = list(cast(Sequence[object], value))
        else:
            raise TypeError("severities must be a string or sequence")
        severities: list[SeverityLevel] = []
        for token in tokens_list:
            severity = (
                token if isinstance(token, SeverityLevel) else SeverityLevel.from_str(str(token))
            )
            if severity not in severities:
                severities.append(severity)
        return _sorted_severity_list(severities)

    @field_validator("targets", mode="before")
    @classmethod
    def _coerce_targets(cls, value: object) -> dict[SeverityLevel, int]:
        if value is None:
            return {}
        if not isinstance(value, Mapping):
            raise TypeError("targets must be a mapping")
        mapping_value = cast(Mapping[object, object], value)
        result: dict[SeverityLevel, int] = {}
        for raw_key, raw_val in mapping_value.items():
            severity = (
                raw_key
                if isinstance(raw_key, SeverityLevel)
                else SeverityLevel.from_str(str(raw_key))
            )
            result[severity] = _parse_budget_value(raw_val)
        return result

    @model_validator(mode="after")
    def _apply_defaults(self) -> RatchetRunBudgetModel:
        severity_set: set[SeverityLevel] = set(self.severities)
        self.severities = _sorted_severity_list(severity_set)
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


class EngineSignaturePayload(TypedDict):
    tool: str | None
    mode: ModeStr | None
    engineOptions: dict[str, JSONValue]


class EngineSignaturePayloadWithHash(EngineSignaturePayload, total=False):
    hash: str


__all__ = [
    "RATCHET_SCHEMA_VERSION",
    "EngineSignaturePayload",
    "EngineSignaturePayloadWithHash",
    "RatchetModel",
    "RatchetPathBudgetModel",
    "RatchetRunBudgetModel",
]
