from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .aggregate import summarise_run
from .types import RunResult


@dataclass(slots=True)
class ManifestBuilder:
    project_root: Path
    data: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.data.update(
            {
                "generatedAt": datetime.now(timezone.utc).isoformat(),
                "projectRoot": str(self.project_root),
                "runs": [],
            }
        )

    def add_run(self, run: RunResult, *, max_depth: int = 3) -> None:
        payload = {
            "tool": run.tool,
            "mode": run.mode,
            "command": run.command,
            "exitCode": run.exit_code,
            "durationMs": run.duration_ms,
        }
        payload.update(summarise_run(run, max_depth=max_depth))
        self.data["runs"].append(payload)

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        import json

        path.write_text(json.dumps(self.data, indent=2) + "\n", encoding="utf-8")

