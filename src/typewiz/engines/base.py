# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from typewiz.config import AuditConfig
from typewiz.core.model_types import CategoryMapping, LogComponent, Mode, OverrideEntry
from typewiz.core.type_aliases import Command, ProfileName, RelPath, ToolName
from typewiz.core.types import Diagnostic
from typewiz.logging import structured_extra
from typewiz.manifest.typed import ToolSummary

logger: logging.Logger = logging.getLogger("typewiz.engine")


def _default_overrides() -> list[OverrideEntry]:
    return []


def _default_category_mapping() -> CategoryMapping:
    return {}


@dataclass(slots=True, frozen=True)
class EngineOptions:
    plugin_args: list[str]
    config_file: Path | None
    include: list[RelPath]
    exclude: list[RelPath]
    profile: ProfileName | None
    overrides: list[OverrideEntry] = field(default_factory=_default_overrides)
    category_mapping: CategoryMapping = field(default_factory=_default_category_mapping)


@dataclass(slots=True, frozen=True)
class EngineContext:
    project_root: Path
    audit_config: AuditConfig
    mode: Mode
    engine_options: EngineOptions


@dataclass(slots=True)
class EngineResult:
    engine: ToolName
    mode: Mode
    command: Command
    exit_code: int
    duration_ms: float
    diagnostics: list[Diagnostic]
    cached: bool = False
    # Optional: raw tool-provided summary counts (normalised to errors/warnings/information/total)
    tool_summary: ToolSummary | None = None

    def __post_init__(self) -> None:
        if not self.command:
            logger.warning(
                "Engine '%s' returned an empty command",
                self.engine,
                extra=structured_extra(component=LogComponent.ENGINE, tool=self.engine),
            )
        if self.duration_ms < 0:
            logger.warning(
                "Engine '%s' reported negative duration %.2f ms",
                self.engine,
                self.duration_ms,
                extra=structured_extra(component=LogComponent.ENGINE, tool=self.engine),
            )
        if self.exit_code < 0:
            logger.warning(
                "Engine '%s' returned negative exit code %s",
                self.engine,
                self.exit_code,
                extra=structured_extra(component=LogComponent.ENGINE, tool=self.engine),
            )


class BaseEngine(Protocol):
    name: str

    def run(self, context: EngineContext, paths: Sequence[RelPath]) -> EngineResult: ...

    def category_mapping(self) -> CategoryMapping:
        """Optional mapping from categories to rule substrings for readiness analysis."""
        return {}

    def fingerprint_targets(
        self,
        context: EngineContext,
        paths: Sequence[RelPath],
    ) -> Sequence[str]:
        """Additional files or globs whose contents should invalidate cached runs."""
        return []
