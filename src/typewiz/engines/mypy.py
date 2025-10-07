from __future__ import annotations

from pathlib import Path
from typing import Sequence

from .base import BaseEngine, EngineContext, EngineResult
from ..runner import run_mypy
from ..utils import python_executable


class MypyEngine(BaseEngine):
    name = "mypy"

    def _args(self, context: EngineContext) -> list[str]:
        return list(context.engine_options.plugin_args)

    def _config_file(self, context: EngineContext) -> Path | None:
        if context.engine_options.config_file:
            return context.engine_options.config_file
        candidate = context.project_root / "mypy.ini"
        return candidate if candidate.exists() else None

    def _build_command(self, context: EngineContext, paths: Sequence[str]) -> list[str]:
        args = self._args(context)
        base = [python_executable(), "-m", "mypy"]
        config_file = self._config_file(context)
        if config_file:
            base.extend(["--config-file", str(config_file)])
        if context.mode == "current":
            command = [*base, "--no-pretty", *args]
        else:
            command = [
                *base,
                "--hide-error-context",
                "--no-error-summary",
                "--show-error-codes",
                "--no-pretty",
                *args,
                *paths,
            ]
        return command

    def run(self, context: EngineContext, paths: Sequence[str]) -> EngineResult:
        command = self._build_command(context, paths)
        return run_mypy(context.project_root, mode=context.mode, command=command)

    def category_mapping(self) -> dict[str, list[str]]:
        return {
            "unknownChecks": [
                # Common mypy error codes indicating unknown/typing issues
                "name-defined",  # missing name/type in scope
                "var-annotated",
                "assignment",
                "arg-type",
                "call-arg",
                "override",
                "return-value",
                "index",
            ],
            "optionalChecks": [
                "union-attr",
                "none",
                "possibly-unbound",
            ],
            "unusedSymbols": [
                "unused-",
            ],
        }

    def fingerprint_targets(self, context: EngineContext, paths: Sequence[str]) -> Sequence[str]:
        targets: list[str] = []
        config = self._config_file(context)
        if config:
            targets.append(str(config))
        return targets


__all__ = ["MypyEngine"]
