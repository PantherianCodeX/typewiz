from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from typewiz.core.model_types import clone_override_entries
from typewiz.core.types import RunResult
from typewiz.runtime import consume, detect_tool_versions, normalise_enums_for_json

from .typed import (
    AggregatedData,
    EngineError,
    EngineOptionsEntry,
    ManifestData,
    RunPayload,
)
from .versioning import CURRENT_MANIFEST_VERSION

logger: logging.Logger = logging.getLogger("typewiz")


@dataclass(slots=True)
class ManifestBuilder:
    project_root: Path
    data: ManifestData = field(init=False)
    fingerprint_truncated: bool = False

    def __post_init__(self) -> None:
        self.data = cast(
            ManifestData,
            {
                "generatedAt": datetime.now(UTC).isoformat(),
                "projectRoot": str(self.project_root),
                "schemaVersion": CURRENT_MANIFEST_VERSION,
                "runs": [],
            },
        )

    def add_run(self, run: RunResult, *, max_depth: int = 3) -> None:
        from typewiz.aggregate import summarise_run

        logger.debug("Adding run: tool=%s mode=%s", run.tool, run.mode)
        summary: AggregatedData = summarise_run(run, max_depth=max_depth)
        options: EngineOptionsEntry = {
            "profile": run.profile,
            "configFile": run.config_file.as_posix() if run.config_file else None,
            "pluginArgs": list(run.plugin_args),
            "include": list(run.include),
            "exclude": list(run.exclude),
            "overrides": clone_override_entries(run.overrides),
            "categoryMapping": {
                key: list(values) for key, values in sorted(run.category_mapping.items())
            },
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
        path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Writing manifest to %s", path)
        # Fill in toolVersions based on tools present in runs
        try:
            tools = sorted({run.get("tool", "") for run in self.data.get("runs", []) if run})
            versions = detect_tool_versions(tools)
            if versions:
                self.data["toolVersions"] = versions
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.debug("Failed to detect tool versions: %s", exc)
        if self.fingerprint_truncated:
            self.data["fingerprintTruncated"] = True
        payload = normalise_enums_for_json(self.data)
        consume(path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8"))
