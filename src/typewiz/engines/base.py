from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, Sequence

from ..config import AuditConfig
from ..types import Diagnostic


@dataclass(slots=True)
class EngineOptions:
    plugin_args: list[str]
    config_file: Path | None
    include: list[str]
    exclude: list[str]
    profile: str | None
    overrides: list[dict[str, object]] = field(default_factory=list)
    category_mapping: dict[str, list[str]] = field(default_factory=dict)


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


class BaseEngine(Protocol):
    name: str

    def run(self, context: EngineContext, paths: Sequence[str]) -> EngineResult:
        ...

    def category_mapping(self) -> dict[str, list[str]]:
        """Optional mapping from categories to rule substrings for readiness analysis."""
        return {}
