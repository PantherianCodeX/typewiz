# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Subprocess helpers and typed command wrappers."""

from __future__ import annotations

import logging
import subprocess  # noqa: S404  # JUSTIFIED: centralised wrapper for safe, allowlisted subprocess execution
import sys
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, cast

from typewiz.core.model_types import LogComponent
from typewiz.logging import structured_extra

logger: logging.Logger = logging.getLogger("typewiz.internal.process")

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

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

    Args:
        args: Command line to execute. The first element is treated as the
            executable and must be a non-empty string.
        cwd: Optional working directory for the child process.
        allowed: Optional allowlist of valid executables. When provided, the
            first element of ``args`` must match one of these entries.

    Returns:
        ``CommandOutput`` containing the executed argument vector along with the
        captured stdout/stderr, exit code, and duration in milliseconds.

    Raises:
        ValueError: If ``args`` is empty or the executable is not allowlisted.
        TypeError: If any argument is falsy (for example ``""``).
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
    debug_details: dict[str, object] = {}
    if cwd:
        debug_details["cwd"] = str(cwd)
    if allowed:
        debug_details["allowed"] = sorted(allowed)
    logger.debug(
        "Executing command: %s",
        " ".join(argv),
        extra=_structured_extra(details=debug_details),
    )
    completed = subprocess.run(  # noqa: S603 - command arguments provided by caller
        argv,
        check=False,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
    )
    duration_ms = (time.perf_counter() - start) * 1000
    if completed.returncode != 0:
        warning_details: dict[str, object] = {}
        if cwd:
            warning_details["cwd"] = str(cwd)
        logger.warning(
            "Command failed (exit=%s): %s",
            completed.returncode,
            " ".join(argv),
            extra=_structured_extra(exit_code=completed.returncode, details=warning_details),
        )
        logging.getLogger().warning(
            "Command failed (exit=%s): %s",
            completed.returncode,
            " ".join(argv),
        )
    return CommandOutput(
        args=argv,
        stdout=completed.stdout,
        stderr=completed.stderr,
        exit_code=completed.returncode,
        duration_ms=duration_ms,
    )


def python_executable() -> str:
    return sys.executable


def _structured_extra(**kwargs: object) -> dict[str, object]:
    payload = structured_extra(LogComponent.SERVICES, **cast("dict[str, Any]", kwargs))
    return cast("dict[str, object]", payload)
