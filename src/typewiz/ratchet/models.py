# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Pydantic models describing ratchet budget files."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import TYPE_CHECKING, Any, ClassVar, Final, Literal, TypedDict, cast

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from typewiz.core.model_types import Mode, SeverityLevel
from typewiz.core.type_aliases import RunId

if TYPE_CHECKING:
    from pathlib import Path

    from typewiz.runtime import JSONValue

type RatchetSchemaVersion = Literal[1]

RATCHET_SCHEMA_VERSION: Final[RatchetSchemaVersion] = 1


def _new_severity_map() -> dict[SeverityLevel, int]:
    """Create an empty severity map.

    Returns:
        dict[SeverityLevel, int]: An empty dictionary mapping severity levels to integer counts.
    """
    return {}


def _sorted_severity_list(values: Iterable[SeverityLevel]) -> list[SeverityLevel]:
    """Sort severity levels by their enum values.

    Args:
        values (Iterable[SeverityLevel]): An iterable of severity levels to sort.

    Returns:
        list[SeverityLevel]: A sorted list of severity levels ordered by their enum values.
    """
    return sorted(values, key=lambda severity: severity.value)


def _default_run_budget_map() -> dict[RunId, RatchetRunBudgetModel]:
    """Create an empty run budget map.

    Returns:
        dict[RunId, RatchetRunBudgetModel]: An empty dictionary mapping run IDs to budget models.
    """
    return {}


def _parse_budget_value(raw: object) -> int:
    """Parse and validate a budget value from a raw object.

    Args:
        raw (object): The raw budget value to parse.

    Returns:
        int: A non-negative integer budget value (minimum 0).
    """
    budget = int(cast("Any", raw))
    return max(budget, 0)


class RatchetPathBudgetModel(BaseModel):
    """Per-path severity budgets."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="forbid")

    severities: dict[SeverityLevel, int] = Field(default_factory=_new_severity_map)

    @field_validator("severities", mode="before")
    @classmethod
    def _coerce_map(cls, value: object) -> dict[SeverityLevel, int]:
        """Validate and coerce the severities mapping.

        Args:
            value (object): The raw severities value to validate.

        Returns:
            dict[SeverityLevel, int]: A validated mapping of severity levels to budget counts.

        Raises:
            TypeError: If value is not a mapping.
        """
        if not isinstance(value, Mapping):
            msg = "severities must be a mapping"
            raise TypeError(msg)
        mapping_value = cast("Mapping[object, object]", value)
        result: dict[SeverityLevel, int] = {}
        for raw_key, raw_val in mapping_value.items():
            severity = cls._parse_severity(raw_key)
            result[severity] = _parse_budget_value(raw_val)
        return result

    @staticmethod
    def _parse_severity(raw: object) -> SeverityLevel:
        """Parse a severity level from a raw object.

        Args:
            raw (object): The raw severity value to parse.

        Returns:
            SeverityLevel: The parsed severity level enum value.
        """
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
        """Normalize and validate the severities field.

        Args:
            value (object): The raw severities value (string or sequence).

        Returns:
            list[SeverityLevel]: A deduplicated, sorted list of severity levels.

        Raises:
            TypeError: If value is not a string or sequence.
        """
        if value is None:
            return []
        if isinstance(value, str):
            tokens_list: list[object] = [part.strip() for part in value.split(",") if part.strip()]
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
            tokens_list = list(cast("Sequence[object]", value))
        else:
            msg = "severities must be a string or sequence"
            raise TypeError(msg)
        severities: list[SeverityLevel] = []
        for token in tokens_list:
            severity = token if isinstance(token, SeverityLevel) else SeverityLevel.from_str(str(token))
            if severity not in severities:
                severities.append(severity)
        return _sorted_severity_list(severities)

    @field_validator("targets", mode="before")
    @classmethod
    def _coerce_targets(cls, value: object) -> dict[SeverityLevel, int]:
        """Validate and coerce the targets mapping.

        Args:
            value (object): The raw targets value to validate.

        Returns:
            dict[SeverityLevel, int]: A validated mapping of severity levels to target counts.

        Raises:
            TypeError: If value is not None and not a mapping.
        """
        if value is None:
            return {}
        if not isinstance(value, Mapping):
            msg = "targets must be a mapping"
            raise TypeError(msg)
        mapping_value = cast("Mapping[object, object]", value)
        result: dict[SeverityLevel, int] = {}
        for raw_key, raw_val in mapping_value.items():
            severity = raw_key if isinstance(raw_key, SeverityLevel) else SeverityLevel.from_str(str(raw_key))
            result[severity] = _parse_budget_value(raw_val)
        return result

    @model_validator(mode="after")
    def _apply_defaults(self) -> RatchetRunBudgetModel:
        """Apply default values and normalize fields after validation.

        Returns:
            RatchetRunBudgetModel: The normalized model instance.
        """
        severity_set: set[SeverityLevel] = set(self.severities)
        self.severities = _sorted_severity_list(severity_set)
        original_paths = cast("Mapping[str, object]", self.paths)
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

    schema_version: RatchetSchemaVersion = Field(
        default=RATCHET_SCHEMA_VERSION,
        alias="schemaVersion",
    )
    generated_at: str = Field(alias="generatedAt")
    manifest_path: Path | None = Field(default=None, alias="manifestPath")
    project_root: Path | None = Field(default=None, alias="projectRoot")
    runs: dict[RunId, RatchetRunBudgetModel] = Field(default_factory=_default_run_budget_map)

    @model_validator(mode="after")
    def _normalise(self) -> RatchetModel:
        """Normalize the runs dictionary after validation.

        Returns:
            RatchetModel: The normalized model instance.
        """
        original_runs = cast("Mapping[str, object]", self.runs)
        self.runs = {
            RunId(str(key)): budget
            if isinstance(budget, RatchetRunBudgetModel)
            else RatchetRunBudgetModel.model_validate(budget)
            for key, budget in sorted(original_runs.items())
        }
        return self


class EngineSignaturePayload(TypedDict):
    """Type checker engine signature information.

    Attributes:
        tool (str | None): The name of the type checking tool used.
        mode (Mode | None): The type checking mode used.
        engineOptions (dict[str, JSONValue]): Engine-specific configuration options.
    """

    tool: str | None
    mode: Mode | None
    engineOptions: dict[str, JSONValue]


class EngineSignaturePayloadWithHash(EngineSignaturePayload, total=False):
    """Engine signature payload with an optional hash field.

    Attributes:
        hash (str): Optional hash of the engine configuration for change detection.
    """

    hash: str


__all__ = [
    "RATCHET_SCHEMA_VERSION",
    "EngineSignaturePayload",
    "EngineSignaturePayloadWithHash",
    "RatchetModel",
    "RatchetPathBudgetModel",
    "RatchetRunBudgetModel",
]
