from __future__ import annotations

import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


logger = logging.getLogger("pytc")


@dataclass(slots=True)
class CommandOutput:
    args: list[str]
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: float


def run_command(args: Iterable[str], cwd: Path | None = None) -> CommandOutput:
    argv = list(args)
    start = time.perf_counter()
    logger.debug("Executing command: %s", " ".join(argv))
    completed = subprocess.run(
        argv,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    duration_ms = (time.perf_counter() - start) * 1000
    if completed.returncode != 0:
        logger.warning("Command failed (exit=%s): %s", completed.returncode, " ".join(argv))
    return CommandOutput(
        args=argv,
        stdout=completed.stdout,
        stderr=completed.stderr,
        exit_code=completed.returncode,
        duration_ms=duration_ms,
    )


def require_json(payload: str, fallback: str | None = None) -> dict:
    data_str = payload.strip() or (fallback or "")
    if not data_str:
        raise ValueError("Expected JSON output but received empty string")
    return json.loads(data_str)


def resolve_project_root(start: Path | None = None) -> Path:
    if start is None:
        start = Path.cwd()
    marker = start / "pyrightconfig.json"
    if marker.exists():
        return start
    for parent in start.parents:
        marker = parent / "pyrightconfig.json"
        if marker.exists():
            return parent
    raise FileNotFoundError("Unable to locate project root (missing pyrightconfig.json)")


def _contains_python(path: Path) -> bool:
    if not path.exists():
        return False
    if path.is_file() and path.suffix in {".py", ".pyi"}:
        return True
    if not path.is_dir():
        return False
    for child in path.iterdir():
        if child.is_file() and child.suffix in {".py", ".pyi"}:
            return True
        if child.is_dir():
            if _contains_python(child):
                return True
    return False


def default_full_paths(root: Path) -> list[str]:
    candidates = [
        "pytc",
        "apps",
        "packages",
        "config",
        "infra",
        "tests",
    ]
    paths: list[str] = []
    for item in candidates:
        full = root / item
        if _contains_python(full):
            paths.append(item)
    return paths


def python_executable() -> str:
    return sys.executable
