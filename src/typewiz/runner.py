from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from pathlib import Path
from typing import cast

from .engines.base import EngineResult
from .types import Diagnostic
from .utils import JSONValue, as_int, as_list, as_mapping, as_str, require_json, run_command

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
    payload: dict[str, JSONValue] = require_json(payload_str)

    diagnostics: list[Diagnostic] = []
    raw_diags = as_list(payload.get("generalDiagnostics", []))
    # Capture tool-provided summary if present
    tool_summary_raw = as_mapping(payload.get("summary") or {})
    try:
        ts_errors = as_int(tool_summary_raw.get("errorCount", 0), 0)
        ts_warnings = as_int(tool_summary_raw.get("warningCount", 0), 0)
        ts_info = as_int(tool_summary_raw.get("informationCount", 0), 0)
        ts_total = ts_errors + ts_warnings + ts_info
        tool_summary: dict[str, int] | None = {
            "errors": ts_errors,
            "warnings": ts_warnings,
            "information": ts_info,
            "total": ts_total,
        }
    except Exception:  # defensive
        tool_summary = None
    for item in raw_diags:
        d = as_mapping(item)
        file_path = as_str(d.get("filePath") or d.get("file") or "")
        if not file_path:
            continue
        rng = as_mapping(d.get("range") or {})
        start = as_mapping(rng.get("start") or {})
        line_num = as_int(start.get("line", 0), 0) + 1  # pyright uses 0-based
        col_num = as_int(start.get("character", 0), 0) + 1
        rule_obj = d.get("rule")
        rule = rule_obj if isinstance(rule_obj, str) else None
        diagnostics.append(
            Diagnostic(
                tool="pyright",
                severity=str(d.get("severity", "error")).lower(),
                path=_make_diag_path(project_root, file_path),
                line=line_num,
                column=col_num,
                code=rule,
                message=str(d.get("message", "")).strip(),
                raw=d,
            )
        )
    diagnostics.sort(key=lambda d: (str(d.path), d.line, d.column))
    # If pyright's own summary (if present) disagrees with parsed diagnostics, log a warning
    if tool_summary is not None:
        parsed_errors = sum(1 for d in diagnostics if d.severity == "error")
        parsed_warnings = sum(1 for d in diagnostics if d.severity == "warning")
        parsed_total = len(diagnostics)
        if (
            parsed_errors != tool_summary.get("errors", parsed_errors)
            or parsed_warnings != tool_summary.get("warnings", parsed_warnings)
            or parsed_total != tool_summary.get("total", parsed_total)
        ):
            logger.warning(
                "pyright summary mismatch: parsed=%s/%s/%s tool=%s/%s/%s",
                parsed_errors,
                parsed_warnings,
                parsed_total,
                tool_summary.get("errors"),
                tool_summary.get("warnings"),
                tool_summary.get("total"),
            )
    engine_result = EngineResult(
        engine="pyright",
        mode=mode,
        command=list(command),
        exit_code=result.exit_code,
        duration_ms=result.duration_ms,
        diagnostics=diagnostics,
        tool_summary=tool_summary,
    )
    logger.debug(
        "pyright run completed: exit=%s diagnostics=%s",
        engine_result.exit_code,
        len(engine_result.diagnostics),
    )
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
                raw=cast(dict[str, object], dict(data)),
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
    logger.debug(
        "mypy run completed: exit=%s diagnostics=%s",
        engine_result.exit_code,
        len(engine_result.diagnostics),
    )
    return engine_result
