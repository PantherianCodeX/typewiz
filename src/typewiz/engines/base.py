from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from ..config import AuditConfig
from ..types import Diagnostic


def _default_overrides() -> list[dict[str, object]]:
    return []


def _default_category_mapping() -> dict[str, list[str]]:
    return {}


@dataclass(slots=True)
class EngineOptions:
    plugin_args: list[str]
    config_file: Path | None
    include: list[str]
    exclude: list[str]
    profile: str | None
    overrides: list[dict[str, object]] = field(default_factory=_default_overrides)
    category_mapping: dict[str, list[str]] = field(default_factory=_default_category_mapping)


@dataclass(slots=True)
class EngineContext:
    project_root: Path
    audit_config: AuditConfig
    mode: str
    engine_options: EngineOptions


@dataclass(slots=True)
class EngineResult:
    engine: str
    mode: str
    command: list[str]
    exit_code: int
    duration_ms: float
    diagnostics: list[Diagnostic]
    cached: bool = False
    # Optional: raw tool-provided summary counts (normalised to errors/warnings/information/total)
    tool_summary: dict[str, int] | None = None


class BaseEngine(Protocol):
    name: str

    def run(self, context: EngineContext, paths: Sequence[str]) -> EngineResult: ...

    def category_mapping(self) -> dict[str, list[str]]:
        """Optional mapping from categories to rule substrings for readiness analysis."""
        return {}

    def fingerprint_targets(self, context: EngineContext, paths: Sequence[str]) -> Sequence[str]:
        """Additional files or globs whose contents should invalidate cached runs."""
        return []
