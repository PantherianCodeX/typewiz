from __future__ import annotations

from typing import List

from .base import PluginCommand, PluginContext, TypingRunner
from ..runner import run_pyright


class PyrightRunner:
    name = "pyright"

    def _args(self, context: PluginContext) -> List[str]:
        return list(context.audit_config.plugin_args.get(self.name, []))

    def generate_commands(self, context: PluginContext) -> list[PluginCommand]:
        args = self._args(context)
        commands: list[PluginCommand] = [
            PluginCommand(self.name, "current", ["pyright", "--outputjson", "--project", "pyrightconfig.json", *args])
        ]
        if context.full_paths:
            commands.append(PluginCommand(self.name, "full", ["pyright", "--outputjson", *args, *context.full_paths]))
        return commands

    def execute(self, context: PluginContext, command: PluginCommand):
        return run_pyright(context.project_root, mode=command.mode, command=command.command)


__all__ = ["PyrightRunner"]
