# Copyright 2025 CrownOps Engineering
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Structured logging utilities shared across ratchetr components."""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Final, Literal, SupportsFloat, SupportsInt, cast

from ratchetr.compat import UTC, TypedDict, Unpack, override
from ratchetr.core.model_types import LogComponent, LogFormat, Mode, SeverityLevel
from ratchetr.json import normalise_enums_for_json

if TYPE_CHECKING:
    from ratchetr.core.type_aliases import RunId, ToolName

ROOT_LOGGER_NAME: Final[str] = "ratchetr"
LOG_FORMAT_ENV: Final[str] = "RATCHETR_LOG_FORMAT"
LOG_LEVEL_ENV: Final[str] = "RATCHETR_LOG_LEVEL"

LOG_FORMATS: Final[tuple[Literal["text", "json"], ...]] = cast(
    "tuple[Literal['text', 'json'], ...]",
    tuple(format_.value for format_ in LogFormat),
)
LOG_LEVELS: Final[tuple[Literal["debug", "info", "warning", "error"], ...]] = (
    "debug",
    "info",
    "warning",
    "error",
)
STRUCTURED_FIELDS: Final[tuple[str, ...]] = (
    "component",
    "tool",
    "mode",
    "duration_ms",
    "counts",
    "cached",
    "exit_code",
    "manifest",
    "path",
    "run_id",
    "signature_matches",
    "fingerprint_truncated",
    "details",
)
CHILD_LOGGERS: Final[tuple[str, ...]] = (
    "ratchetr.cli",
    "ratchetr.cache",
    "ratchetr.engine",
    "ratchetr.engine.registry",
    "ratchetr.dashboard",
    "ratchetr.ratchet",
    "ratchetr.services",
    "ratchetr.manifest",
)


@dataclass(slots=True, frozen=True)
class LogConfig:
    """Resolved logging configuration for diagnostics and debugging."""

    format: LogFormat
    level: int
    level_name: str


class JSONLogFormatter(logging.Formatter):
    """Render log records as structured JSON objects."""

    @override
    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as a JSON string.

        Args:
            record: Log record to serialise.

        Returns:
            JSON-formatted string containing standard and structured fields.
        """
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname.lower(),
            "message": record.getMessage(),
            "logger": record.name,
        }
        for field in STRUCTURED_FIELDS:
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


def _coerce_log_level(level: str | int) -> tuple[int, str]:
    if isinstance(level, int):
        return level, logging.getLevelName(level).lower()
    value = str(level).strip().lower()
    match value:
        case "debug":
            return logging.DEBUG, "debug"
        case "warning":
            return logging.WARNING, "warning"
        case "error":
            return logging.ERROR, "error"
        case _:
            return logging.INFO, "info"


def _select_format(preferred: LogFormat | str | None) -> LogFormat:
    if preferred is not None:
        return _coerce_log_format(preferred)
    env_value = os.getenv(LOG_FORMAT_ENV)
    return _coerce_log_format(env_value) if env_value else LogFormat.TEXT


def _select_level(level: str | int | None) -> tuple[int, str]:
    if level is not None:
        return _coerce_log_level(level)
    env_value = os.getenv(LOG_LEVEL_ENV)
    if env_value:
        return _coerce_log_level(env_value)
    return _coerce_log_level("info")


def _configure_handler(log_format: LogFormat) -> logging.Handler:
    handler = logging.StreamHandler()
    if log_format is LogFormat.JSON:
        handler.setFormatter(JSONLogFormatter())
    else:
        handler.setFormatter(TextLogFormatter())
    return handler


def _apply_child_levels(level: int, children: Iterable[str]) -> None:
    for child in children:
        logging.getLogger(child).setLevel(level)


def configure_logging(
    log_format: LogFormat | str | None = None,
    *,
    log_level: str | int | None = None,
) -> LogConfig:
    """Configure ratchetr logging according to the requested format and level.

    Args:
        log_format: Desired log output format. ``None`` falls back to the
            ``RATCHETR_LOG_FORMAT`` environment variable or ``text``.
        log_level: Preferred verbosity (string or numeric). ``None`` consults
            ``RATCHETR_LOG_LEVEL`` or defaults to ``info``.

    Returns:
        A ``LogConfig`` describing the selected formatter and resolved numeric
        log level, which is also applied to the root and child loggers.
    """
    selected_format = _select_format(log_format)
    level_value, level_name = _select_level(log_level)

    root_logger = logging.getLogger(ROOT_LOGGER_NAME)
    root_logger.handlers.clear()
    root_logger.addHandler(_configure_handler(selected_format))
    root_logger.setLevel(level_value)
    root_logger.propagate = False

    _apply_child_levels(level_value, CHILD_LOGGERS)
    return LogConfig(format=selected_format, level=level_value, level_name=level_name)


class _StructuredLogBase(TypedDict):
    component: LogComponent


class StructuredLogExtra(_StructuredLogBase, total=False):
    """Structured logging extras accepted by ratchetr log records."""

    tool: str
    mode: Mode
    duration_ms: float
    counts: Mapping[SeverityLevel, int]
    cached: bool
    exit_code: int
    manifest: str
    path: str
    run_id: str
    signature_matches: bool
    fingerprint_truncated: bool
    details: Mapping[str, object]


class _StructuredLogKwargs(TypedDict, total=False):
    tool: ToolName | str
    mode: Mode | str
    duration_ms: float
    counts: Mapping[SeverityLevel, int]
    cached: bool
    exit_code: int
    manifest: str | os.PathLike[str]
    path: str | os.PathLike[str]
    run_id: RunId | str
    signature_matches: bool
    fingerprint_truncated: bool
    details: Mapping[str, object]


def _normalise_mode(value: Mode | str | None) -> Mode | None:
    if value is None:
        return None
    return value if isinstance(value, Mode) else Mode.from_str(str(value))


def _normalise_path(value: object) -> str | None:
    if value is None:
        return None
    return os.fspath(cast("str | os.PathLike[str]", value))


def _to_float(value: object) -> float:
    return float(cast("SupportsFloat | str | float", value))


def _to_bool(value: object) -> bool:
    return bool(value)


def _to_int(value: object) -> int:
    return int(cast("SupportsInt | str | int", value))


def _maybe_assign(
    extra: StructuredLogExtra,
    *,
    key: str,
    kwargs: dict[str, object],
    transform: Callable[[object], object | None] | None = None,
) -> None:
    if key not in kwargs:
        return
    value = kwargs[key]
    if value is None:
        return
    if transform is not None:
        value = transform(value)
        if value is None:
            return
    cast("dict[str, object]", extra)[key] = value


def structured_extra(
    component: LogComponent,
    **kwargs: Unpack[_StructuredLogKwargs],
) -> StructuredLogExtra:
    """Return a consistently typed ``logging.extra`` payload.

    Args:
        component: Logical logging component for the record.
        **kwargs: Optional structured fields (tool, mode, duration, counts, etc.).

    Returns:
        Mapping suitable for the ``extra`` parameter when emitting log records.
    """
    extra: StructuredLogExtra = {"component": component}
    payload_kwargs = cast("dict[str, object]", kwargs)
    _maybe_assign(extra, key="tool", kwargs=payload_kwargs, transform=str)
    mode_value = _normalise_mode(cast("Mode | str | None", payload_kwargs.get("mode")))
    if mode_value is not None:
        extra["mode"] = mode_value
    _maybe_assign(extra, key="duration_ms", kwargs=payload_kwargs, transform=_to_float)
    counts = payload_kwargs.get("counts")
    if isinstance(counts, Mapping) and counts:
        extra["counts"] = dict(cast("Mapping[SeverityLevel, int]", counts))
    _maybe_assign(extra, key="cached", kwargs=payload_kwargs, transform=_to_bool)
    _maybe_assign(extra, key="exit_code", kwargs=payload_kwargs, transform=_to_int)
    _maybe_assign(
        extra,
        key="manifest",
        kwargs=payload_kwargs,
        transform=_normalise_path,
    )
    _maybe_assign(
        extra,
        key="path",
        kwargs=payload_kwargs,
        transform=_normalise_path,
    )
    _maybe_assign(extra, key="run_id", kwargs=payload_kwargs, transform=str)
    _maybe_assign(extra, key="signature_matches", kwargs=payload_kwargs, transform=_to_bool)
    _maybe_assign(
        extra,
        key="fingerprint_truncated",
        kwargs=payload_kwargs,
        transform=_to_bool,
    )
    details = payload_kwargs.get("details")
    if isinstance(details, Mapping) and details:
        extra["details"] = dict(cast("Mapping[str, object]", details))
    return extra


__all__ = [
    "LOG_FORMATS",
    "LOG_LEVELS",
    "LogConfig",
    "StructuredLogExtra",
    "configure_logging",
    "structured_extra",
]
