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

"""Test doubles and stubs for isolating dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, cast

from ratchetr.core.model_types import Mode
from ratchetr.core.type_aliases import ToolName
from ratchetr.engines.base import EngineContext, EngineResult

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ratchetr.core.types import Diagnostic, RunResult
    from ratchetr.manifest.typed import ToolSummary

__all__ = ["AuditStubEngine", "EngineInvocation", "RecordingEngine", "StubEngine"]


class StubEngine:
    """Simple engine stub that records invocations."""

    name: str

    DEFAULT_CATEGORY_MAPPING: ClassVar[dict[str, list[str]]] = {}
    DEFAULT_FINGERPRINT_TARGETS: ClassVar[tuple[str, ...]] = ()

    def __init__(self, result: RunResult, expected_profile: str | None = None) -> None:
        """Initialise the stub with a canned `RunResult`outcome."""
        super().__init__()
        self.name = "stub"
        self._result = result
        self.expected_profile = expected_profile
        self.invocations: list[tuple[Mode, list[str], list[str]]] = []

    def run(self, context: EngineContext, paths: Sequence[str]) -> EngineResult:
        """Execute a stubbed engine run and record the invocation.

        Records invocation details for later verification in tests. Returns different
        results based on the execution mode: empty diagnostics for TARGET mode, or
        the pre-configured result for other modes.

        Note:
            If expected_profile is set, asserts that it matches the context's profile.

        Args:
            context: Execution context containing mode, options, and configuration.
            paths: File paths to be analyzed by the engine.

        Returns:
            EngineResult containing command, exit code, duration, and diagnostics.
            For TARGET mode, returns a clean result with no diagnostics. For other
            modes, returns the pre-configured result from initialization.
        """
        if self.expected_profile is not None:
            assert context.engine_options.profile == self.expected_profile
        self.invocations.append(
            (context.mode, list(context.engine_options.plugin_args), list(paths)),
        )
        tool_name = ToolName(self.name)
        if context.mode is Mode.TARGET:
            return EngineResult(
                engine=tool_name,
                mode=context.mode,
                command=["stub", *paths],
                exit_code=0,
                duration_ms=0.2,
                diagnostics=[],
            )
        return EngineResult(
            engine=tool_name,
            mode=context.mode,
            command=list(self._result.command),
            exit_code=self._result.exit_code,
            duration_ms=self._result.duration_ms,
            diagnostics=list(self._result.diagnostics),
        )

    def category_mapping(self) -> dict[str, list[str]]:
        """Return the category mapping configuration.

        Returns:
            A copy of the default category mapping dictionary.
        """
        return dict(self.DEFAULT_CATEGORY_MAPPING)

    def fingerprint_targets(self, _context: EngineContext, _paths: Sequence[str]) -> Sequence[str]:
        """Determine which files should be fingerprinted.

        Returns:
            A list of file paths to fingerprint, from the default configuration.
        """
        return list(self.DEFAULT_FINGERPRINT_TARGETS)


class AuditStubEngine:
    """Stub used by API tests to emulate target/current runs."""

    name: str

    DEFAULT_CATEGORY_MAPPING: ClassVar[dict[str, list[str]]] = {"unknownChecks": ["reportGeneralTypeIssues"]}
    DEFAULT_FINGERPRINT_TARGETS: ClassVar[tuple[str, ...]] = ()

    def __init__(self, result: RunResult) -> None:
        """Prime the stub engine with a single `RunResult`payload."""
        super().__init__()
        self.name = "stub"
        self._result = result

    def run(self, context: EngineContext, _paths: Sequence[str]) -> EngineResult:
        """Execute a stubbed audit run for target/current mode testing.

        Emulates engine execution for API tests that need to distinguish between
        TARGET and CURRENT mode runs. Returns empty diagnostics for CURRENT mode,
        or the pre-configured result with tool summary for other modes.

        Args:
            context: Execution context containing mode, options, and configuration.

        Returns:
            EngineResult containing command, exit code, duration, diagnostics, and
            optionally a tool summary. For CURRENT mode, returns a clean result with
            no diagnostics or summary. For other modes, returns the pre-configured
            result from initialization including any tool summary.
        """
        tool_name = ToolName(self.name)
        if context.mode is Mode.CURRENT:
            return EngineResult(
                engine=tool_name,
                mode=context.mode,
                command=["stub", "current"],
                exit_code=0,
                duration_ms=0.1,
                diagnostics=[],
            )
        tool_summary = (
            cast("ToolSummary", dict(self._result.tool_summary)) if self._result.tool_summary is not None else None
        )
        return EngineResult(
            engine=tool_name,
            mode=context.mode,
            command=list(self._result.command),
            exit_code=self._result.exit_code,
            duration_ms=self._result.duration_ms,
            diagnostics=list(self._result.diagnostics),
            tool_summary=tool_summary,
        )

    def category_mapping(self) -> dict[str, list[str]]:
        """Return the category mapping configuration.

        Returns:
            A copy of the default category mapping dictionary.
        """
        return dict(self.DEFAULT_CATEGORY_MAPPING)

    def fingerprint_targets(self, _context: EngineContext, _paths: Sequence[str]) -> Sequence[str]:
        """Determine which files should be fingerprinted.

        Returns:
            A list of file paths to fingerprint, from the default configuration.
        """
        return list(self.DEFAULT_FINGERPRINT_TARGETS)


@dataclass(slots=True)
class EngineInvocation:
    """Record of a single engine invocation."""

    context: EngineContext
    plugin_args: list[str]
    paths: list[str]
    profile: str | None

    @property
    def mode(self) -> Mode:
        """Get the execution mode from the context.

        Returns:
            The execution mode (TARGET or CURRENT) from the invocation context.
        """
        return self.context.mode


class RecordingEngine:
    """Engine stub that records invocations and replays canned diagnostics."""

    name = "stub"

    def __init__(
        self,
        *,
        diagnostics: Sequence[Diagnostic] | None = None,
        tool_summary_on_target: ToolSummary | None = None,
        target_exit_code: int = 0,
        current_exit_code: int = 0,
        category_mapping: dict[str, list[str]] | None = None,
        fingerprint_targets: Sequence[str] | None = None,
    ) -> None:
        """Set up the recording engine with canned diagnostics and metadata."""
        super().__init__()
        self._diagnostics = list(diagnostics or [])
        self._tool_summary_on_target = tool_summary_on_target
        self._target_exit_code = target_exit_code
        self._current_exit_code = current_exit_code
        self._category_mapping = category_mapping or {}
        self._fingerprint_targets = tuple(fingerprint_targets or ())
        self.invocations: list[EngineInvocation] = []

    def run(self, context: EngineContext, paths: Sequence[str]) -> EngineResult:
        """Execute a stubbed engine run and record detailed invocation data.

        Records comprehensive invocation details including context, plugin arguments,
        paths, and profile for later inspection in tests. Returns pre-configured
        diagnostics and exit codes that vary based on execution mode.

        Args:
            context: Execution context containing mode, options, and configuration.
            paths: File paths to be analyzed by the engine.

        Returns:
            EngineResult containing command, exit code, duration, diagnostics, and
            optionally a tool summary. Exit code is determined by mode (TARGET uses
            target_exit_code, CURRENT uses current_exit_code). Tool summary is only
            included for TARGET mode when configured during initialization.
        """
        invocation = EngineInvocation(
            context=context,
            plugin_args=list(context.engine_options.plugin_args),
            paths=list(paths),
            profile=context.engine_options.profile,
        )
        self.invocations.append(invocation)
        exit_code = self._target_exit_code if context.mode is Mode.TARGET else self._current_exit_code
        tool_summary = (
            cast("ToolSummary", dict(self._tool_summary_on_target))
            if context.mode is Mode.TARGET and self._tool_summary_on_target is not None
            else None
        )
        return EngineResult(
            engine=ToolName(self.name),
            mode=context.mode,
            command=["stub", str(context.mode)],
            exit_code=exit_code,
            duration_ms=0.1,
            diagnostics=list(self._diagnostics),
            tool_summary=tool_summary,
        )

    def category_mapping(self) -> dict[str, list[str]]:
        """Return the category mapping configuration.

        Returns:
            A copy of the configured category mapping dictionary.
        """
        return dict(self._category_mapping)

    def fingerprint_targets(self, _context: EngineContext, _paths: Sequence[str]) -> Sequence[str]:
        """Determine which files should be fingerprinted.

        Returns:
            A list of file paths to fingerprint, from the configured targets.
        """
        return list(self._fingerprint_targets)
