# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Pyright type checker engine implementation for TypeWiz.

This module provides the PyrightEngine class, which implements the BaseEngine
protocol for running pyright as a type checker. It handles command construction,
configuration file detection, and JSON output parsing for pyright.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from typewiz.core.model_types import CategoryMapping, Mode
from typewiz.engines.base import BaseEngine, EngineContext, EngineResult
from typewiz.engines.execution import run_pyright

if TYPE_CHECKING:
    from collections.abc import Sequence

    from typewiz.core.type_aliases import Command, RelPath


class PyrightEngine(BaseEngine):
    """Type checker engine implementation for pyright.

    This engine runs pyright on Python projects, handling configuration file
    detection, command-line argument construction, and JSON output parsing.
    It supports both CURRENT mode (full project analysis) and DELTA mode
    (targeted file analysis).

    Attributes:
        name: The engine identifier "pyright".
    """

    name = "pyright"

    @staticmethod
    def _args(context: EngineContext) -> list[str]:
        """Extract additional command-line arguments from context.

        Args:
            context: Execution context containing engine options.

        Returns:
            list[str]: List of additional arguments to pass to pyright.
        """
        return list(context.engine_options.plugin_args)

    def _build_command(self, context: EngineContext, paths: Sequence[RelPath]) -> Command:
        """Build the pyright command-line invocation.

        Constructs the complete command to run pyright with JSON output,
        including configuration file selection, mode-specific behavior, and
        target paths. In CURRENT mode, analyzes the full project using the
        config file or project root. In DELTA mode, analyzes only the
        specified paths.

        Args:
            context: Execution context with mode, config, and project info.
            paths: Sequence of relative paths to analyze.

        Returns:
            Command: Complete command-line as a list of strings.
        """
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
        """Execute pyright on the specified paths.

        Builds the pyright command and delegates to the execution layer to run
        the tool and parse its JSON output into structured diagnostics.

        Args:
            context: Execution context including project root and configuration.
            paths: Sequence of relative paths to analyze.

        Returns:
            EngineResult: Results including diagnostics, exit code, and timing.
        """
        command = self._build_command(context, paths)
        return run_pyright(context.project_root, mode=context.mode, command=command)

    @override
    @staticmethod
    def category_mapping() -> CategoryMapping:
        """Provide pyright-specific diagnostic category mappings.

        Maps TypeWiz diagnostic categories to pyright error code patterns for
        readiness analysis. Categories include unknownChecks (Unknown/Untyped
        issues), optionalChecks (Optional/None issues), and unusedSymbols.

        Returns:
            CategoryMapping: Dictionary mapping category names to pyright error codes.
        """
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
    def fingerprint_targets(self, context: EngineContext, paths: Sequence[RelPath]) -> Sequence[str]:
        """Specify pyright config files for cache invalidation.

        Returns the path to pyrightconfig.json (explicit or default) if it
        exists, ensuring that cached results are invalidated when the pyright
        configuration changes.

        Args:
            context: Execution context including project root and configuration.
            paths: Sequence of relative paths being analyzed (unused).

        Returns:
            Sequence[str]: List containing the config file path if found.
        """
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
