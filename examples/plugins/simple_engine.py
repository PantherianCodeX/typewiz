# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from typewiz.engines.base import BaseEngine, EngineContext, EngineResult
from typewiz.types import Diagnostic

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass
class SimpleEngine(BaseEngine):
    """A minimal example engine that emits a single information diagnostic.

    This demonstrates the engine protocol used by typewiz. You can package
    engines and expose them via entry points to integrate with typewiz.
    """

    name: str = "simple"

    def run(self, context: EngineContext, paths: Sequence[str]) -> EngineResult:
        diag = Diagnostic(
            tool=self.name,
            severity="information",
            path=context.project_root / "example.py",
            line=1,
            column=1,
            code="S000",
            message="SimpleEngine example diagnostic",
            raw={},
        )
        return EngineResult(
            engine=self.name,
            mode=context.mode,
            command=[self.name, context.mode],
            exit_code=0,
            duration_ms=0.1,
            diagnostics=[diag],
        )

    def fingerprint_targets(self, context: EngineContext, paths: Sequence[str]) -> Sequence[str]:
        # No extra fingerprints required for this example
        return []
