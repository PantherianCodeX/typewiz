# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Test doubles and stubs for isolating dependencies."""

from __future__ import annotations

from collections.abc import Sequence

from typewiz.core.model_types import Mode
from typewiz.core.type_aliases import ToolName
from typewiz.core.types import RunResult
from typewiz.engines.base import EngineContext, EngineResult

__all__ = ["StubEngine"]


class StubEngine:
    """Simple engine stub that records invocations."""

    name: str

    def __init__(self, result: RunResult, expected_profile: str | None = None) -> None:
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
        return {}

    def fingerprint_targets(self, context: EngineContext, paths: Sequence[str]) -> Sequence[str]:
        return []
