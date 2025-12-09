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

"""Minimal ratchetr engine implementation used for documentation and tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ratchetr.compat import override
from ratchetr.core.model_types import SeverityLevel
from ratchetr.core.type_aliases import ToolName
from ratchetr.core.types import Diagnostic
from ratchetr.engines.base import BaseEngine, EngineContext, EngineResult

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass
class SimpleEngine(BaseEngine):
    """A minimal example engine that emits a single information diagnostic.

    This demonstrates the engine protocol used by ratchetr. You can package
    engines and expose them via entry points to integrate with ratchetr.
    """

    name: str = "simple"

    @override
    def run(self, context: EngineContext, paths: Sequence[str]) -> EngineResult:
        """Produce a deterministic diagnostic payload for demonstration purposes.

        Args:
            context: Execution context containing the project root and mode.
            paths: The file paths ratchetr asked the engine to analyse (unused in
                this sample engine).

        Returns:
            An ``EngineResult`` containing a single informational diagnostic that
            proves the plugin integration pipeline is functioning.
        """
        tool_name = ToolName(self.name)
        analyzed_paths = [context.project_root / candidate for candidate in paths]
        diag = Diagnostic(
            tool=tool_name,
            severity=SeverityLevel.INFORMATION,
            path=analyzed_paths[0] if analyzed_paths else context.project_root / "example.py",
            line=1,
            column=1,
            code="S000",
            message="SimpleEngine example diagnostic",
            raw={},
        )
        return EngineResult(
            engine=tool_name,
            mode=context.mode,
            command=[self.name, context.mode, *[str(path) for path in paths]],
            exit_code=0,
            duration_ms=0.1,
            diagnostics=[diag],
        )

    @override
    def fingerprint_targets(self, context: EngineContext, paths: Sequence[str]) -> Sequence[str]:
        """Declare files that influence the engine's cached fingerprint state.

        The simple engine does not persist cacheable artefacts, so returning an
        empty list ensures caching stays opt-in for educational purposes.

        Args:
            context: Execution context provided for parity with other engines.
            paths: Candidate paths for the run (unused).

        Returns:
            An empty sequence because this demonstration engine has no
            additional fingerprint dependencies.
        """
        return [f"{self.name}:{context.project_root / candidate}" for candidate in paths]
