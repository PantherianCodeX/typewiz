# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Final, Literal, TypedDict, cast, override

from ..core.model_types import LogComponent, LogFormat, Mode, SeverityLevel
from ..utils import normalise_enums_for_json

LOG_FORMATS: Final[tuple[Literal["text", "json"], ...]] = cast(
    tuple[Literal["text", "json"], ...],
    tuple(format_.value for format_ in LogFormat),
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


def configure_logging(log_format: LogFormat | str) -> None:
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
    root_logger.setLevel(logging.INFO)
    root_logger.propagate = False

    # Ensure child loggers inherit the configured handler/level.
    for child in (
        "typewiz.cli",
        "typewiz.cache",
        "typewiz.engine",
        "typewiz.engine.registry",
        "typewiz.dashboard",
    ):
        logging.getLogger(child).setLevel(logging.INFO)


class StructuredLogExtra(TypedDict, total=False):
    component: LogComponent
    tool: str
    mode: Mode
    duration_ms: float
    counts: dict[SeverityLevel, int]
    cached: bool
    exit_code: int


__all__ = ["LOG_FORMATS", "StructuredLogExtra", "configure_logging"]
