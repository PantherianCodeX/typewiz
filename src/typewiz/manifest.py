from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from .aggregate import summarise_run
from .typed_manifest import AggregatedData, EngineOptionsEntry, ManifestData, RunPayload
from .types import RunResult

logger = logging.getLogger("typewiz")


@dataclass(slots=True)
class ManifestBuilder:
    project_root: Path
    data: ManifestData = field(init=False)

    def __post_init__(self) -> None:
        self.data = cast(
            ManifestData,
            {
                "generatedAt": datetime.now(UTC).isoformat(),
                "projectRoot": str(self.project_root),
                "runs": [],
            },
        )

    def add_run(self, run: RunResult, *, max_depth: int = 3) -> None:
        logger.debug("Adding run: tool=%s mode=%s", run.tool, run.mode)
        summary: AggregatedData = summarise_run(run, max_depth=max_depth)
        options: EngineOptionsEntry = {
            "profile": run.profile,
            "configFile": str(run.config_file) if run.config_file else None,
            "pluginArgs": list(run.plugin_args),
            "include": list(run.include),
            "exclude": list(run.exclude),
            "overrides": [dict(item) for item in run.overrides],
            "categoryMapping": {
                key: list(values) for key, values in sorted(run.category_mapping.items())
            },
        }
        payload: RunPayload = {
            "tool": run.tool,
            "mode": run.mode,
            "command": run.command,
            "exitCode": run.exit_code,
            "durationMs": run.duration_ms,
            "summary": summary["summary"],
            "perFile": summary["perFile"],
            "perFolder": summary["perFolder"],
            "engineOptions": options,
        }
        if run.tool_summary:
            payload["toolSummary"] = {
                "errors": int(run.tool_summary.get("errors", 0)),
                "warnings": int(run.tool_summary.get("warnings", 0)),
                "information": int(run.tool_summary.get("information", 0)),
                "total": int(run.tool_summary.get("total", 0)),
            }
        self.data["runs"].append(payload)

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Writing manifest to %s", path)
        path.write_text(json.dumps(self.data, indent=2) + "\n", encoding="utf-8")
