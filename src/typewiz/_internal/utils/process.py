"""Subprocess helpers and typed command wrappers."""

from __future__ import annotations

import logging
import subprocess
import sys
import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

logger: logging.Logger = logging.getLogger("typewiz")

if TYPE_CHECKING:
    from typewiz.core.type_aliases import Command

__all__ = ["CommandOutput", "python_executable", "run_command"]


@dataclass(slots=True)
class CommandOutput:
    args: Command
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: float


def run_command(
    args: Iterable[str],
    cwd: Path | None = None,
    *,
    allowed: set[str] | None = None,
) -> CommandOutput:
    """Run a subprocess safely and return its captured output.

    Security guardrails:
    - Requires an iterable of string arguments; never uses ``shell=True``.
    - Optionally enforces an allowlist for the executable (first arg) via ``allowed``.
    """
    argv: Command = list(args)
    if not argv:
        raise ValueError
    if not all(a for a in argv):
        raise TypeError
    executable = argv[0]
    if allowed is not None and executable not in allowed:
        raise ValueError
    start = time.perf_counter()
    logger.debug("Executing command: %s", " ".join(argv))
    completed = subprocess.run(  # noqa: S603 - command arguments provided by caller
        argv,
        check=False,
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


def python_executable() -> str:
    return sys.executable
