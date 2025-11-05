from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Literal, override

LOG_FORMATS = ("text", "json")


class JSONLogFormatter(logging.Formatter):
    """Render log records as structured JSON objects."""

    @override
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=None).isoformat(),
            "level": record.levelname.lower(),
            "message": record.getMessage(),
            "logger": record.name,
        }
        for field in ("component", "tool", "mode", "duration_ms", "counts", "cached", "exit_code"):
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class TextLogFormatter(logging.Formatter):
    """Readable, single-line formatter for CLI output."""

    def __init__(self) -> None:
        super().__init__("[%(levelname)s] %(message)s")


def configure_logging(log_format: Literal["text", "json"]) -> None:
    """Configure Typewiz logging according to the requested format."""

    handler = logging.StreamHandler()
    if log_format == "json":
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


__all__ = ["LOG_FORMATS", "configure_logging"]
