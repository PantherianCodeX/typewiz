from __future__ import annotations

from typing import List

from .base import PluginCommand, PluginContext, TypingRunner
from ..runner import run_mypy
from ..utils import python_executable


class MypyRunner:
    name = "mypy"

    def _args(self, context: PluginContext) -> List[str]:
        return list(context.audit_config.plugin_args.get(self.name, []))

    def generate_commands(self, context: PluginContext) -> list[PluginCommand]:
        args = self._args(context)
        base = [python_executable(), "-m", "mypy", "--config-file", "mypy.ini"]
        commands: list[PluginCommand] = [
            PluginCommand(self.name, "current", [*base, "--no-pretty", *args])
        ]
        if context.full_paths:
            commands.append(
                PluginCommand(
                    self.name,
                    "full",
                    [*base, "--hide-error-context", "--no-error-summary", "--show-error-codes", "--no-pretty", *args, *context.full_paths],
                )
            )
        return commands

    def execute(self, context: PluginContext, command: PluginCommand):
        return run_mypy(context.project_root, mode=command.mode, command=command.command)


__all__ = ["MypyRunner"]
