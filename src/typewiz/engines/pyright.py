# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

from collections.abc import Sequence
from typing import override

from typewiz.core.model_types import CategoryMapping, Mode
from typewiz.core.type_aliases import Command, RelPath
from typewiz.engines.base import BaseEngine, EngineContext, EngineResult
from typewiz.engines.execution import run_pyright


class PyrightEngine(BaseEngine):
    name = "pyright"

    def _args(self, context: EngineContext) -> list[str]:
        return list(context.engine_options.plugin_args)

    def _build_command(self, context: EngineContext, paths: Sequence[RelPath]) -> Command:
        args = self._args(context)
        default_config = context.project_root / "pyrightconfig.json"
        config_path = context.engine_options.config_file
        command: Command = ["pyright", "--outputjson"]
        if context.mode is Mode.CURRENT:
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
            command.extend(str(path) for path in paths)
        else:
            command.append(str(context.project_root))
        return command

    @override
    def run(self, context: EngineContext, paths: Sequence[RelPath]) -> EngineResult:
        command = self._build_command(context, paths)
        return run_pyright(context.project_root, mode=context.mode, command=command)

    @override
    def category_mapping(self) -> CategoryMapping:
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

    @override
    def fingerprint_targets(
        self, context: EngineContext, paths: Sequence[RelPath]
    ) -> Sequence[str]:
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
