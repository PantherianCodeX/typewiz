from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from typewiz.config import AuditConfig
from typewiz.model_types import CategoryMapping, Mode, OverrideEntry
from typewiz.typed_manifest import ToolSummary
from typewiz.types import Diagnostic

logger: logging.Logger = logging.getLogger("typewiz.engine")


def _default_overrides() -> list[OverrideEntry]:
    return []


def _default_category_mapping() -> CategoryMapping:
    return {}


@dataclass(slots=True)
class EngineOptions:
    plugin_args: list[str]
    config_file: Path | None
    include: list[str]
    exclude: list[str]
    profile: str | None
    overrides: list[OverrideEntry] = field(default_factory=_default_overrides)
    category_mapping: CategoryMapping = field(default_factory=_default_category_mapping)


@dataclass(slots=True)
class EngineContext:
    project_root: Path
    audit_config: AuditConfig
    mode: Mode
    engine_options: EngineOptions


@dataclass(slots=True)
class EngineResult:
    engine: str
    mode: Mode
    command: list[str]
    exit_code: int
    duration_ms: float
    diagnostics: list[Diagnostic]
    cached: bool = False
    # Optional: raw tool-provided summary counts (normalised to errors/warnings/information/total)
    tool_summary: ToolSummary | None = None

    def __post_init__(self) -> None:
        if not self.command:
            logger.warning("Engine '%s' returned an empty command", self.engine)
        if self.duration_ms < 0:
            logger.warning(
                "Engine '%s' reported negative duration %.2f ms", self.engine, self.duration_ms
            )
        if self.exit_code < 0:
            logger.warning(
                "Engine '%s' returned negative exit code %s", self.engine, self.exit_code
            )


class BaseEngine(Protocol):
    name: str

    def run(self, context: EngineContext, paths: Sequence[str]) -> EngineResult: ...

    def category_mapping(self) -> CategoryMapping:
        """Optional mapping from categories to rule substrings for readiness analysis."""
        return {}

    def fingerprint_targets(self, context: EngineContext, paths: Sequence[str]) -> Sequence[str]:
        """Additional files or globs whose contents should invalidate cached runs."""
        return []
