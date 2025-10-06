from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable, Sequence

from .types import Diagnostic, RunResult
from .utils import require_json, run_command


def _make_diag_path(project_root: Path, file_path: str) -> Path:
    path = Path(file_path)
    try:
        return path.resolve().relative_to(project_root)
    except ValueError:
        return path.resolve()


def run_pyright(
    project_root: Path,
    *,
    mode: str,
    command: Sequence[str],
) -> RunResult:
    result = run_command(command, cwd=project_root)
    payload_str = result.stdout or result.stderr
    payload = require_json(payload_str)
    diagnostics: list[Diagnostic] = []
    for diag in payload.get("generalDiagnostics", []):
        file_path = str(diag.get("filePath") or diag.get("file") or "")
        if not file_path:
            continue
        rng = diag.get("range") or {}
        start = rng.get("start") or {}
        diagnostics.append(
            Diagnostic(
                tool="pyright",
                severity=str(diag.get("severity", "error")).lower(),
                path=_make_diag_path(project_root, file_path),
                line=int(start.get("line", 0)) + 1,
                column=int(start.get("character", 0)) + 1,
                code=diag.get("rule"),
                message=str(diag.get("message", "")).strip(),
                raw=diag,
            )
        )
    return RunResult(
        tool="pyright",
        mode=mode,
        command=list(command),
        exit_code=result.exit_code,
        duration_ms=result.duration_ms,
        diagnostics=diagnostics,
    )


_MYPY_LINE = re.compile(
    r"^(?P<path>.+?):(?P<line>\d+):(?:(?P<column>\d+):)? (?P<severity>error|note|warning): (?P<message>.*?)(?: \[(?P<code>[^\]]+)\])?$"
)


def run_mypy(
    project_root: Path,
    *,
    mode: str,
    command: Sequence[str],
) -> RunResult:
    result = run_command(command, cwd=project_root)
    diagnostics: list[Diagnostic] = []
    remaining_stderr = result.stderr.strip()
    if remaining_stderr:
        # mypy may emit structural errors here (e.g., config issues). capture as pseudo diagnostics.
        diagnostics.append(
            Diagnostic(
                tool="mypy",
                severity="error",
                path=Path("<stderr>"),
                line=0,
                column=0,
                code=None,
                message=remaining_stderr,
                raw={"stderr": remaining_stderr},
            )
        )
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("Found ") or line.startswith("Success:"):
            continue
        match = _MYPY_LINE.match(line)
        if not match:
            diagnostics.append(
                Diagnostic(
                    tool="mypy",
                    severity="error",
                    path=Path("<parse-error>"),
                    line=0,
                    column=0,
                    code=None,
                    message=line,
                    raw={"unparsed": line},
                )
            )
            continue
        data = match.groupdict()
        diag_path = _make_diag_path(project_root, data["path"])
        diagnostics.append(
            Diagnostic(
                tool="mypy",
                severity=data["severity"].lower(),
                path=diag_path,
                line=int(data["line"]),
                column=int(data.get("column") or 0),
                code=data.get("code"),
                message=data["message"].strip(),
                raw=data,
            )
        )
    return RunResult(
        tool="mypy",
        mode=mode,
        command=list(command),
        exit_code=result.exit_code,
        duration_ms=result.duration_ms,
        diagnostics=diagnostics,
    )
