from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

from ..config import AuditConfig
from ..types import RunResult


@dataclass(frozen=True)
class PluginCommand:
    runner: str
    mode: str
    command: list[str]


@dataclass(frozen=True)
class PluginContext:
    project_root: Path
    full_paths: Sequence[str]
    audit_config: AuditConfig


class TypingRunner(Protocol):
    name: str

    def generate_commands(self, context: PluginContext) -> list[PluginCommand]:
        ...

    def execute(self, context: PluginContext, command: PluginCommand) -> RunResult:
        ...
