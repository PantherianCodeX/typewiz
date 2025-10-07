from __future__ import annotations

import re
from pathlib import Path
from typing import Sequence, TypedDict, NotRequired
import logging

from .engines.base import EngineResult
from .types import Diagnostic
from typing import Any, Dict
from .utils import require_json, run_command

logger = logging.getLogger("typewiz")

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
) -> EngineResult:
    logger.info("Running pyright (%s)", " ".join(command))
    result = run_command(command, cwd=project_root)
    payload_str = result.stdout or result.stderr
    payload: Dict[str, Any] = require_json(payload_str)

    class _Pos(TypedDict):
        line: int
        character: int

    class _Range(TypedDict):
        start: _Pos

    class _PyrightDiag(TypedDict, total=False):
        filePath: str
        file: str
        severity: str
        message: str
        rule: str
        range: _Range

    diagnostics: list[Diagnostic] = []
    raw_diags = payload.get("generalDiagnostics", [])
    for diag in raw_diags:  # type: ignore[assignment]
        d = diag  # runtime trust
        file_path = str(d.get("filePath") or d.get("file") or "")
        if not file_path:
            continue
        rng = d.get("range") or {}
        start = rng.get("start") or {}
        diagnostics.append(
            Diagnostic(
                tool="pyright",
                severity=str(d.get("severity", "error")).lower(),
                path=_make_diag_path(project_root, file_path),
                line=int(start.get("line", 0)) + 1,
                column=int(start.get("character", 0)) + 1,
                code=d.get("rule"),
                message=str(d.get("message", "")).strip(),
                raw=d,
            )
        )
    diagnostics.sort(key=lambda d: (str(d.path), d.line, d.column))
    engine_result = EngineResult(
        engine="pyright",
        mode=mode,
        command=list(command),
        exit_code=result.exit_code,
        duration_ms=result.duration_ms,
        diagnostics=diagnostics,
    )
    logger.debug("pyright run completed: exit=%s diagnostics=%s", engine_result.exit_code, len(engine_result.diagnostics))
    return engine_result


_MYPY_LINE = re.compile(
    r"^(?P<path>.+?):(?P<line>\d+):(?:(?P<column>\d+):)? (?P<severity>error|note|warning): (?P<message>.*?)(?: \[(?P<code>[^\]]+)\])?$"
)


def run_mypy(
    project_root: Path,
    *,
    mode: str,
    command: Sequence[str],
) -> EngineResult:
    logger.info("Running mypy (%s)", " ".join(command))
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
    diagnostics.sort(key=lambda d: (str(d.path), d.line, d.column))
    engine_result = EngineResult(
        engine="mypy",
        mode=mode,
        command=list(command),
        exit_code=result.exit_code,
        duration_ms=result.duration_ms,
        diagnostics=diagnostics,
    )
    logger.debug("mypy run completed: exit=%s diagnostics=%s", engine_result.exit_code, len(engine_result.diagnostics))
    return engine_result
