from __future__ import annotations

from collections.abc import Sequence

from ..runner import run_pyright
from .base import BaseEngine, EngineContext, EngineResult


class PyrightEngine(BaseEngine):
    name = "pyright"

    def _args(self, context: EngineContext) -> list[str]:
        return list(context.engine_options.plugin_args)

    def _build_command(self, context: EngineContext, paths: Sequence[str]) -> list[str]:
        args = self._args(context)
        default_config = context.project_root / "pyrightconfig.json"
        config_path = context.engine_options.config_file
        command: list[str] = ["pyright", "--outputjson"]
        if context.mode == "current":
            if config_path:
                command.extend(["--project", str(config_path)])
            elif default_config.exists():
                command.extend(["--project", str(default_config)])
            else:
                command.append(str(context.project_root))
            command.extend(args)
            return command

        if config_path:
            command.extend(["--project", str(config_path)])
        command.extend(args)
        if paths:
            command.extend(paths)
        else:
            command.append(str(context.project_root))
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
            if default.exists():
                targets.append(str(default))
        return targets


__all__ = ["PyrightEngine"]
