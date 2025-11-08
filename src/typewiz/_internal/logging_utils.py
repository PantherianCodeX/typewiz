# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Final, Literal, TypedDict, cast, override

from typewiz._internal.utils import normalise_enums_for_json
from typewiz.core.model_types import LogComponent, LogFormat, Mode, SeverityLevel

LOG_FORMATS: Final[tuple[Literal["text", "json"], ...]] = cast(
    tuple[Literal["text", "json"], ...],
    tuple(format_.value for format_ in LogFormat),
)
LOG_LEVELS: Final[tuple[Literal["debug", "info", "warning", "error"], ...]] = (
    "debug",
    "info",
    "warning",
    "error",
)


class JSONLogFormatter(logging.Formatter):
    """Render log records as structured JSON objects."""

    @override
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname.lower(),
            "message": record.getMessage(),
            "logger": record.name,
        }
        for field in ("component", "tool", "mode", "duration_ms", "counts", "cached", "exit_code"):
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(normalise_enums_for_json(payload), ensure_ascii=False)


class TextLogFormatter(logging.Formatter):
    """Readable, single-line formatter for CLI output."""

    def __init__(self) -> None:
        super().__init__("[%(levelname)s] %(message)s")


def _coerce_log_format(log_format: LogFormat | str) -> LogFormat:
    if isinstance(log_format, LogFormat):
        return log_format
    return LogFormat.from_str(log_format)


def _coerce_log_level(level: str | int) -> int:
    if isinstance(level, int):
        return level
    value = str(level).strip().lower()
    match value:
        case "debug":
            return logging.DEBUG
        case "warning":
            return logging.WARNING
        case "error":
            return logging.ERROR
        case _:
            return logging.INFO


def configure_logging(log_format: LogFormat | str, *, log_level: str | int = "info") -> None:
    """Configure Typewiz logging according to the requested format."""

    selected_format = _coerce_log_format(log_format)
    handler = logging.StreamHandler()
    if selected_format is LogFormat.JSON:
        handler.setFormatter(JSONLogFormatter())
    else:
        handler.setFormatter(TextLogFormatter())

    root_logger = logging.getLogger("typewiz")
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(_coerce_log_level(log_level))
    root_logger.propagate = False

    # Ensure child loggers inherit the configured handler/level.
    for child in (
        "typewiz.cli",
        "typewiz.cache",
        "typewiz.engine",
        "typewiz.engine.registry",
        "typewiz.dashboard",
    ):
        logging.getLogger(child).setLevel(_coerce_log_level(log_level))


class StructuredLogExtra(TypedDict, total=False):
    component: LogComponent
    tool: str
    mode: Mode
    duration_ms: float
    counts: dict[SeverityLevel, int]
    cached: bool
    exit_code: int


__all__ = ["LOG_FORMATS", "LOG_LEVELS", "StructuredLogExtra", "configure_logging"]
