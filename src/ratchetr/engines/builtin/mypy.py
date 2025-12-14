# Copyright 2025 CrownOps Engineering
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Mypy type checker engine implementation for ratchetr.

This module provides the MypyEngine class, which implements the BaseEngine
protocol for running mypy as a type checker. It handles command construction,
configuration file detection, and result parsing for mypy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ratchetr.compat import override
from ratchetr.engines.base import BaseEngine, EngineContext, EngineResult
from ratchetr.engines.execution import run_mypy
from ratchetr.runtime import python_executable

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from ratchetr.core.model_types import CategoryMapping
    from ratchetr.core.type_aliases import Command, RelPath


class MypyEngine(BaseEngine):
    """Type checker engine implementation for mypy.

    This engine runs mypy on Python projects, handling configuration file
    detection, command-line argument construction, and result parsing.
    It supports both CURRENT mode (targeted file analysis) and TARGET mode.

    Attributes:
        name: The engine identifier "mypy".
    """

    name = "mypy"

    @staticmethod
    def _args(context: EngineContext) -> list[str]:
        """Extract additional command-line arguments from context.

        Args:
            context: Execution context containing engine options.

        Returns:
            list[str]: List of additional arguments to pass to mypy.
        """
        return list(context.engine_options.plugin_args)

    def _config_file(self, context: EngineContext) -> Path | None:
        """Determine the mypy configuration file to use.

        Checks for an explicitly configured file first, then falls back to
        looking for mypy.ini in the project root.

        Args:
            context: Execution context containing engine options and project root.

        Returns:
            Path | None: Path to the configuration file if found, None otherwise.
        """
        _ = self
        if context.engine_options.config_file:
            return context.engine_options.config_file
        candidate = context.project_root / "mypy.ini"
        return candidate if candidate.exists() else None

    def _build_command(self, context: EngineContext, paths: Sequence[RelPath]) -> Command:
        """Build the mypy command-line invocation (mode-agnostic).

        Constructs the complete command to run mypy using module invocation
        (`python -m mypy`). Mode-agnostic: accepts resolved paths and doesn't
        branch on context.mode.

        Args:
            context: Execution context with config and project info.
            paths: Sequence of relative paths to analyze.

        Returns:
            Command: Complete command-line as a list of strings.
        """
        args = self._args(context)
        command: Command = [python_executable(), "-m", "mypy"]

        # Config selection (mode-agnostic)
        config_file = self._config_file(context)
        if config_file:
            command.extend(["--config-file", str(config_file)])

        # Standard mypy flags for structured output
        command.extend([
            "--hide-error-context",
            "--no-error-summary",
            "--show-error-codes",
            "--no-pretty",
        ])

        # Add engine-specific args
        command.extend(args)

        # Add paths
        if paths:
            command.extend(str(path) for path in paths)

        return command

    @override
    def run(self, context: EngineContext, paths: Sequence[RelPath]) -> EngineResult:
        """Execute mypy on the specified paths.

        Builds the mypy command and delegates to the execution layer to run
        the tool and parse its output into structured diagnostics.

        Args:
            context: Execution context including project root and configuration.
            paths: Sequence of relative paths to analyze.

        Returns:
            EngineResult: Results including diagnostics, exit code, and timing.
        """
        command = self._build_command(context, paths)
        return run_mypy(context.project_root, mode=context.mode, command=command)

    @override
    @staticmethod
    def category_mapping() -> CategoryMapping:
        """Provide mypy-specific diagnostic category mappings.

        Maps ratchetr diagnostic categories to mypy error code patterns for
        readiness analysis. Categories include unknownChecks (type inference
        issues), optionalChecks (None/Optional issues), and unusedSymbols.

        Returns:
            CategoryMapping: Dictionary mapping category names to mypy error codes.
        """
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

    @override
    def fingerprint_targets(
        self,
        context: EngineContext,
        # ignore JUSTIFIED: protocol requires a paths parameter for structural parity;
        # this implementation derives targets from configuration instead
        paths: Sequence[RelPath],  # noqa: ARG002
    ) -> Sequence[str]:
        """Specify mypy config files for cache invalidation.

        Returns the path to mypy.ini if it exists, ensuring that cached results
        are invalidated when the mypy configuration changes.

        Args:
            context: Execution context including project root and configuration.
            paths: Sequence of relative paths being analyzed (unused).

        Returns:
            Sequence[str]: List containing the config file path if found.
        """
        targets: list[str] = []
        config = self._config_file(context)
        if config:
            targets.append(str(config))
        return targets


__all__ = ["MypyEngine"]
