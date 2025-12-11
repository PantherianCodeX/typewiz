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

"""Build and write manifest files from type checking run results.

This module provides the ManifestBuilder class for constructing typing audit
manifests. The builder aggregates results from multiple type checking runs
and writes them to JSON format with tool version detection and metadata.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, cast

from ratchetr.compat import UTC
from ratchetr.core.model_types import LogComponent, clone_override_entries
from ratchetr.json import normalise_enums_for_json
from ratchetr.logging import structured_extra
from ratchetr.runtime import consume, detect_tool_versions

from .aggregate import summarise_run
from .versioning import CURRENT_MANIFEST_VERSION

if TYPE_CHECKING:
    from pathlib import Path

    from ratchetr.core.types import RunResult

    from .typed import (
        AggregatedData,
        EngineError,
        EngineOptionsEntry,
        ManifestData,
        RunPayload,
    )

logger: logging.Logger = logging.getLogger("ratchetr.manifest.builder")


@dataclass(slots=True)
class ManifestBuilder:
    """Builder for constructing typing audit manifest files.

    Aggregates results from multiple type checking runs and generates a
    structured manifest with metadata, summaries, and detailed diagnostics.

    Attributes:
        project_root: Root directory of the project being audited.
        data: ManifestData dictionary containing all manifest content.
        fingerprint_truncated: Whether fingerprint data was truncated.
    """

    project_root: Path
    data: ManifestData = field(init=False)
    fingerprint_truncated: bool = False

    def __post_init__(self) -> None:
        """Initialize manifest data with metadata and empty runs list."""
        self.data = cast(
            "ManifestData",
            {
                "generatedAt": datetime.now(UTC).isoformat(),
                "projectRoot": str(self.project_root),
                "schemaVersion": CURRENT_MANIFEST_VERSION,
                "runs": [],
            },
        )

    def add_run(self, run: RunResult, *, max_depth: int = 3) -> None:
        """Add a type checking run to the manifest.

        Summarizes the run's diagnostics and appends it to the manifest's runs list.
        Includes engine options, tool summary, and error information if available.

        Args:
            run: RunResult containing diagnostics and configuration.
            max_depth: Maximum folder depth for aggregation (default: 3).
        """
        logger.debug(
            "Adding run: tool=%s mode=%s",
            run.tool,
            run.mode,
            extra=structured_extra(
                component=LogComponent.MANIFEST,
                tool=str(run.tool),
                mode=run.mode,
                details={"max_depth": max_depth},
            ),
        )
        summary: AggregatedData = summarise_run(run, max_depth=max_depth)
        options: EngineOptionsEntry = {
            "profile": run.profile,
            "configFile": run.config_file.as_posix() if run.config_file else None,
            "pluginArgs": list(run.plugin_args),
            "include": list(run.include),
            "exclude": list(run.exclude),
            "overrides": clone_override_entries(run.overrides),
            "categoryMapping": {key: list(values) for key, values in sorted(run.category_mapping.items())},
        }
        payload: RunPayload = {
            "tool": str(run.tool),
            "mode": run.mode,
            "command": run.command,
            "exitCode": run.exit_code,
            "durationMs": run.duration_ms,
            "summary": summary["summary"],
            "perFile": summary["perFile"],
            "perFolder": summary["perFolder"],
            "engineOptions": options,
        }
        # Reproducibility helpers
        payload["engineArgsEffective"] = list(run.plugin_args)
        payload["scannedPathsResolved"] = list(run.scanned_paths)
        if run.tool_summary:
            payload["toolSummary"] = {
                "errors": int(run.tool_summary.get("errors", 0)),
                "warnings": int(run.tool_summary.get("warnings", 0)),
                "information": int(run.tool_summary.get("information", 0)),
                "total": int(run.tool_summary.get("total", 0)),
            }
        if run.engine_error:
            err = run.engine_error
            engine_err: EngineError = {}
            msg = err.get("message")
            if isinstance(msg, str) and msg:
                engine_err["message"] = msg
            exitv = err.get("exitCode")
            if isinstance(exitv, int):
                engine_err["exitCode"] = exitv
            stderrv = err.get("stderr")
            if isinstance(stderrv, str) and stderrv:
                engine_err["stderr"] = stderrv
            if engine_err:
                payload["engineError"] = engine_err
        runs_list = self.data.setdefault("runs", [])
        runs_list.append(payload)

    def write(self, path: Path) -> None:
        """Write the manifest to a JSON file.

        Creates parent directories if needed, detects tool versions from runs,
        normalizes enums for JSON serialization, and writes formatted output.

        Args:
            path: Path where the manifest JSON file should be written.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        logger.info(
            "Writing manifest to %s",
            path,
            extra=structured_extra(component=LogComponent.MANIFEST, path=path),
        )
        # Fill in toolVersions based on tools present in runs
        try:
            tools = sorted({run.get("tool", "") for run in self.data.get("runs", []) if run})
            versions = detect_tool_versions(tools)
            if versions:
                self.data["toolVersions"] = versions
        # ignore JUSTIFIED: tool version detection is best-effort; failures are logged
        # and handled gracefully
        except (OSError, ValueError, RuntimeError) as exc:  # pragma: no cover - tool version detection errors
            # OSError: subprocess/filesystem errors
            # ValueError: invalid tool names or version parsing
            # RuntimeError: tool execution failures
            logger.debug(
                "Failed to detect tool versions: %s",
                exc,
                extra=structured_extra(component=LogComponent.MANIFEST),
            )
        if self.fingerprint_truncated:
            self.data["fingerprintTruncated"] = True
        payload = normalise_enums_for_json(self.data)
        consume(path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8"))
