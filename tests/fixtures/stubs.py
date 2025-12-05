# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Test doubles and stubs for isolating dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, cast

from typewiz.core.model_types import Mode
from typewiz.core.type_aliases import ToolName
from typewiz.engines.base import EngineContext, EngineResult

if TYPE_CHECKING:
    from collections.abc import Sequence

    from typewiz.core.types import Diagnostic, RunResult
    from typewiz.manifest.typed import ToolSummary

__all__ = ["AuditStubEngine", "EngineInvocation", "RecordingEngine", "StubEngine"]


class StubEngine:
    """Simple engine stub that records invocations."""

    name: str

    DEFAULT_CATEGORY_MAPPING: ClassVar[dict[str, list[str]]] = {}
    DEFAULT_FINGERPRINT_TARGETS: ClassVar[tuple[str, ...]] = ()

    def __init__(self, result: RunResult, expected_profile: str | None = None) -> None:
        """Initialise the stub with a canned ``RunResult`` outcome."""
        super().__init__()
        self.name = "stub"
        self._result = result
        self.expected_profile = expected_profile
        self.invocations: list[tuple[Mode, list[str], list[str]]] = []

    def run(self, context: EngineContext, paths: Sequence[str]) -> EngineResult:
        if self.expected_profile is not None:
            assert context.engine_options.profile == self.expected_profile
        self.invocations.append(
            (context.mode, list(context.engine_options.plugin_args), list(paths)),
        )
        tool_name = ToolName(self.name)
        if context.mode is Mode.FULL:
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
        return dict(self.DEFAULT_CATEGORY_MAPPING)

    def fingerprint_targets(self, _context: EngineContext, _paths: Sequence[str]) -> Sequence[str]:
        return list(self.DEFAULT_FINGERPRINT_TARGETS)


class AuditStubEngine:
    """Stub used by API tests to emulate full/current runs."""

    name: str

    DEFAULT_CATEGORY_MAPPING: ClassVar[dict[str, list[str]]] = {"unknownChecks": ["reportGeneralTypeIssues"]}
    DEFAULT_FINGERPRINT_TARGETS: ClassVar[tuple[str, ...]] = ()

    def __init__(self, result: RunResult) -> None:
        """Prime the stub engine with a single ``RunResult`` payload."""
        super().__init__()
        self.name = "stub"
        self._result = result

    def run(self, context: EngineContext, _paths: Sequence[str]) -> EngineResult:
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
        return dict(self.DEFAULT_CATEGORY_MAPPING)

    def fingerprint_targets(self, _context: EngineContext, _paths: Sequence[str]) -> Sequence[str]:
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
        return self.context.mode


class RecordingEngine:
    """Engine stub that records invocations and replays canned diagnostics."""

    name = "stub"

    def __init__(
        self,
        *,
        diagnostics: Sequence[Diagnostic] | None = None,
        tool_summary_on_full: ToolSummary | None = None,
        full_exit_code: int = 0,
        current_exit_code: int = 0,
        category_mapping: dict[str, list[str]] | None = None,
        fingerprint_targets: Sequence[str] | None = None,
    ) -> None:
        """Set up the recording engine with canned diagnostics and metadata."""
        super().__init__()
        self._diagnostics = list(diagnostics or [])
        self._tool_summary_on_full = tool_summary_on_full
        self._full_exit_code = full_exit_code
        self._current_exit_code = current_exit_code
        self._category_mapping = category_mapping or {}
        self._fingerprint_targets = tuple(fingerprint_targets or ())
        self.invocations: list[EngineInvocation] = []

    def run(self, context: EngineContext, paths: Sequence[str]) -> EngineResult:
        invocation = EngineInvocation(
            context=context,
            plugin_args=list(context.engine_options.plugin_args),
            paths=list(paths),
            profile=context.engine_options.profile,
        )
        self.invocations.append(invocation)
        exit_code = self._full_exit_code if context.mode is Mode.FULL else self._current_exit_code
        tool_summary = (
            cast("ToolSummary", dict(self._tool_summary_on_full))
            if context.mode is Mode.FULL and self._tool_summary_on_full is not None
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
        return dict(self._category_mapping)

    def fingerprint_targets(self, _context: EngineContext, _paths: Sequence[str]) -> Sequence[str]:
        return list(self._fingerprint_targets)
