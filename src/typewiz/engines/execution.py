# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Final, cast

from typewiz.core.model_types import LogComponent, Mode, SeverityLevel
from typewiz.core.type_aliases import BuiltinEngineName, Command, ToolName
from typewiz.core.types import Diagnostic
from typewiz.engines.base import EngineResult
from typewiz.logging import StructuredLogExtra, structured_extra
from typewiz.manifest.typed import ToolSummary
from typewiz.runtime import (
    JSONValue,
    as_int,
    as_list,
    as_mapping,
    as_str,
    require_json,
    run_command,
)

logger: logging.Logger = logging.getLogger("typewiz.engines.execution")
PYRIGHT_NAME: Final[BuiltinEngineName] = "pyright"
MYPY_NAME: Final[BuiltinEngineName] = "mypy"
PYRIGHT_TOOL: Final[ToolName] = ToolName(PYRIGHT_NAME)
MYPY_TOOL: Final[ToolName] = ToolName(MYPY_NAME)


def _make_diag_path(project_root: Path, file_path: str) -> Path:
    path = Path(file_path)
    try:
        return path.resolve().relative_to(project_root)
    except ValueError:
        return path.resolve()


def run_pyright(
    project_root: Path,
    *,
    mode: Mode,
    command: Sequence[str],
) -> EngineResult:
    start_extra: StructuredLogExtra = structured_extra(
        component=LogComponent.ENGINE,
        tool="pyright",
        mode=mode,
    )
    argv: Command = list(command)
    logger.info(
        "Running pyright (%s)",
        " ".join(argv),
        extra=start_extra,
    )
    result = run_command(argv, cwd=project_root, allowed={"pyright"})
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
        tool_summary: ToolSummary | None = {
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
        severity = SeverityLevel.coerce(d.get("severity") or SeverityLevel.ERROR)
        diagnostics.append(
            Diagnostic(
                tool=PYRIGHT_TOOL,
                severity=severity,
                path=_make_diag_path(project_root, file_path),
                line=line_num,
                column=col_num,
                code=rule,
                message=str(d.get("message", "")).strip(),
                raw=d,
            ),
        )
    diagnostics.sort(key=lambda d: (str(d.path), d.line, d.column))
    # If pyright's own summary (if present) disagrees with parsed diagnostics, log a warning
    if tool_summary is not None:
        parsed_errors = sum(1 for d in diagnostics if d.severity is SeverityLevel.ERROR)
        parsed_warnings = sum(1 for d in diagnostics if d.severity is SeverityLevel.WARNING)
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
                extra=structured_extra(
                    component=LogComponent.ENGINE,
                    tool="pyright",
                    mode=mode,
                    details={
                        "parsed": (parsed_errors, parsed_warnings, parsed_total),
                        "tool": (
                            tool_summary.get("errors"),
                            tool_summary.get("warnings"),
                            tool_summary.get("total"),
                        ),
                    },
                ),
            )
    engine_result = EngineResult(
        engine=PYRIGHT_TOOL,
        mode=mode,
        command=argv,
        exit_code=result.exit_code,
        duration_ms=result.duration_ms,
        diagnostics=diagnostics,
        tool_summary=tool_summary,
    )
    debug_extra: StructuredLogExtra = structured_extra(
        component=LogComponent.ENGINE,
        tool="pyright",
        mode=mode,
        duration_ms=engine_result.duration_ms,
        exit_code=engine_result.exit_code,
        details={"diagnostics": len(engine_result.diagnostics)},
    )
    logger.debug(
        "pyright run completed: exit=%s diagnostics=%s",
        engine_result.exit_code,
        len(engine_result.diagnostics),
        extra=debug_extra,
    )
    return engine_result


_MYPY_LINE: Final[re.Pattern[str]] = re.compile(
    r"^(?P<path>.+?):(?P<line>\d+):(?:(?P<column>\d+):)? "
    + r"(?P<severity>error|note|warning): (?P<message>.*?)"
    + r"(?: \[(?P<code>[^\]]+)\])?$"
)


def run_mypy(
    project_root: Path,
    *,
    mode: Mode,
    command: Sequence[str],
) -> EngineResult:
    start_extra: StructuredLogExtra = structured_extra(
        component=LogComponent.ENGINE,
        tool="mypy",
        mode=mode,
    )
    argv: Command = list(command)
    logger.info(
        "Running mypy (%s)",
        " ".join(argv),
        extra=start_extra,
    )
    result = run_command(
        argv,
        cwd=project_root,
        allowed={argv[0]},
    )
    diagnostics: list[Diagnostic] = []
    remaining_stderr = result.stderr.strip()
    if remaining_stderr:
        # mypy may emit structural errors here (e.g., config issues). capture as pseudo diagnostics.
        diagnostics.append(
            Diagnostic(
                tool=MYPY_TOOL,
                severity=SeverityLevel.ERROR,
                path=Path("<stderr>"),
                line=0,
                column=0,
                code=None,
                message=remaining_stderr,
                raw={"stderr": remaining_stderr},
            ),
        )
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line or line.startswith("Found ") or line.startswith("Success:"):
            continue
        match = _MYPY_LINE.match(line)
        if not match:
            diagnostics.append(
                Diagnostic(
                    tool=MYPY_TOOL,
                    severity=SeverityLevel.ERROR,
                    path=Path("<parse-error>"),
                    line=0,
                    column=0,
                    code=None,
                    message=line,
                    raw={"unparsed": line},
                ),
            )
            continue
        data = match.groupdict()
        diag_path = _make_diag_path(project_root, data["path"])
        severity = SeverityLevel.coerce(data.get("severity") or SeverityLevel.ERROR)
        diagnostics.append(
            Diagnostic(
                tool=MYPY_TOOL,
                severity=severity,
                path=diag_path,
                line=int(data["line"]),
                column=int(data.get("column") or 0),
                code=data.get("code"),
                message=data["message"].strip(),
                raw=cast(dict[str, JSONValue], dict(data)),
            ),
        )
    diagnostics.sort(key=lambda d: (str(d.path), d.line, d.column))
    engine_result = EngineResult(
        engine=MYPY_TOOL,
        mode=mode,
        command=argv,
        exit_code=result.exit_code,
        duration_ms=result.duration_ms,
        diagnostics=diagnostics,
    )
    debug_extra: StructuredLogExtra = structured_extra(
        component=LogComponent.ENGINE,
        tool="mypy",
        mode=mode,
        duration_ms=engine_result.duration_ms,
        exit_code=engine_result.exit_code,
        details={"diagnostics": len(engine_result.diagnostics)},
    )
    logger.debug(
        "mypy run completed: exit=%s diagnostics=%s",
        engine_result.exit_code,
        len(engine_result.diagnostics),
        extra=debug_extra,
    )
    return engine_result
