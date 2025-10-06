from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from typing import cast

from .aggregate import summarise_run
from .typed_manifest import AggregatedData, ManifestData, RunPayload
from .types import RunResult

logger = logging.getLogger("pytc")


@dataclass(slots=True)
class ManifestBuilder:
    project_root: Path
    data: ManifestData = field(init=False)

    def __post_init__(self) -> None:
        self.data = cast(
            ManifestData,
            {
                "generatedAt": datetime.now(timezone.utc).isoformat(),
                "projectRoot": str(self.project_root),
                "runs": [],
            },
        )

    def add_run(self, run: RunResult, *, max_depth: int = 3) -> None:
        logger.debug("Adding run: tool=%s mode=%s", run.tool, run.mode)
        summary: AggregatedData = summarise_run(run, max_depth=max_depth)
        payload: RunPayload = {
            "tool": run.tool,
            "mode": run.mode,
            "command": run.command,
            "exitCode": run.exit_code,
            "durationMs": run.duration_ms,
            "summary": summary["summary"],
            "perFile": summary["perFile"],
            "perFolder": summary["perFolder"],
        }
        self.data["runs"].append(payload)

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Writing manifest to %s", path)
        path.write_text(json.dumps(self.data, indent=2) + "\n", encoding="utf-8")
