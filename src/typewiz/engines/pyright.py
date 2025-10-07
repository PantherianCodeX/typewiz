from __future__ import annotations

from typing import Sequence

from .base import BaseEngine, EngineContext, EngineResult
from ..runner import run_pyright


class PyrightEngine(BaseEngine):
    name = "pyright"

    def _args(self, context: EngineContext) -> list[str]:
        return list(context.engine_options.plugin_args)

    def _build_command(self, context: EngineContext, paths: Sequence[str]) -> list[str]:
        args = self._args(context)
        config_path = context.engine_options.config_file
        if context.mode == "current":
            project_arg = (
                str(config_path)
                if config_path
                else str((context.project_root / "pyrightconfig.json"))
            )
            command = ["pyright", "--outputjson", "--project", project_arg, *args]
        else:
            command = ["pyright", "--outputjson"]
            if config_path:
                command.extend(["--project", str(config_path)])
            command.extend(args)
            command.extend(paths)
        return command

    def run(self, context: EngineContext, paths: Sequence[str]) -> EngineResult:
        command = self._build_command(context, paths)
        return run_pyright(context.project_root, mode=context.mode, command=command)

    def category_mapping(self) -> dict[str, list[str]]:
        return {
            "unknownChecks": [
                "reportUnknown",
                "reportMissingType",
                "reportUntyped",
                "Unknown",
            ],
            "optionalChecks": [
                "reportOptional",
                "None",
            ],
            "unusedSymbols": [
                "reportUnused",
                "redundant",
            ],
        }

    def fingerprint_targets(self, context: EngineContext, paths: Sequence[str]) -> Sequence[str]:
        targets: list[str] = []
        config = context.engine_options.config_file
        if config:
            targets.append(str(config))
        else:
            default = context.project_root / "pyrightconfig.json"
            targets.append(str(default))
        return targets


__all__ = ["PyrightEngine"]
