from __future__ import annotations

import json
import logging
import subprocess
import sys
import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

logger = logging.getLogger("typewiz")

# JSON typing helpers
# A recursive JSON value used for parsing engine outputs safely.
# Use PEP 695 type alias for a clean, recursive definition under Python 3.12+
type JSONValue = (str | int | float | bool | None | dict[str, JSONValue] | list[JSONValue])

ROOT_MARKERS: tuple[str, ...] = (
    "typewiz.toml",
    ".typewiz.toml",
    "pyproject.toml",
)


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
        capture_output=True,
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


def require_json(payload: str, fallback: str | None = None) -> dict[str, JSONValue]:
    data_str = payload.strip() or (fallback or "")
    if not data_str:
        raise ValueError("Expected JSON output but received empty string")
    return cast(dict[str, JSONValue], json.loads(data_str))


def as_mapping(value: object) -> dict[str, JSONValue]:
    return cast(dict[str, JSONValue], value) if isinstance(value, dict) else {}


def as_list(value: object) -> list[JSONValue]:
    return cast(list[JSONValue], value) if isinstance(value, list) else []


def as_str(value: object, default: str = "") -> str:
    if isinstance(value, str):
        return value
    return default


def as_int(value: object, default: int = 0) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def resolve_project_root(start: Path | None = None) -> Path:
    base = (start or Path.cwd()).resolve()
    if base.is_file():
        base = base.parent

    checked: list[Path] = []
    for candidate in (base, *base.parents):
        checked.append(candidate)
        for marker in ROOT_MARKERS:
            if (candidate / marker).exists():
                return candidate

    if start is not None:
        if not base.exists():
            raise FileNotFoundError(f"Provided project root {start} does not exist.")
        logger.debug(
            "No project markers found; using provided path %s as project root",
            base,
        )
        return base

    logger.debug(
        "No project markers found in %s; using current working directory as root",
        ", ".join(str(path) for path in checked),
    )
    return base


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
        "typewiz",
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
    if not paths:
        paths.append(".")
    return paths


def python_executable() -> str:
    return sys.executable
