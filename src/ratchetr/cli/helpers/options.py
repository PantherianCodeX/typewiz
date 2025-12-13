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

"""Centralised CLI option registration and parsing utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

from ratchetr.cli.helpers.args import ArgumentRegistrar, register_argument
from ratchetr.compat import StrEnum
from ratchetr.core.model_types import ReadinessLevel, ReadinessStatus, SeverityLevel
from ratchetr.paths import OutputFormat, OutputTarget, PathOverrides

if TYPE_CHECKING:
    import argparse
    from collections.abc import Collection, Iterable, Sequence


READINESS_TOKENS_HELP = (
    "Use key=value tokens (level=, status=, limit=, severity=) and boolean toggles (details/no-details)."
)


class StdoutFormat(StrEnum):
    """Supported stdout rendering formats."""

    TEXT = "text"
    JSON = "json"

    @classmethod
    def from_str(cls, raw: str) -> StdoutFormat:
        """Normalise and validate stdout format tokens.

        Args:
            raw: Raw string provided via CLI or configuration.

        Returns:
            StdoutFormat: Matching enum value.

        Raises:
            SystemExit: If the format is unsupported.
        """
        token = raw.strip().lower()
        try:
            return cls(token)
        except ValueError as exc:
            message = f"Unknown output format '{raw}'"
            raise SystemExit(message) from exc


@dataclass(slots=True, frozen=True)
class SaveFlag:
    """Parsed state for save-style CLI flags."""

    provided: bool
    targets: tuple[OutputTarget, ...]


@dataclass(slots=True, frozen=True)
class ReadinessOptions:
    """Parsed readiness token state."""

    enabled: bool
    level: ReadinessLevel
    statuses: tuple[ReadinessStatus, ...] | None
    limit: int
    severities: tuple[SeverityLevel, ...] | None
    include_details: bool


def register_path_overrides(parser: ArgumentRegistrar) -> None:
    """Register global path override flags.

    Args:
        parser: Argument registrar to attach arguments to.
    """
    register_argument(
        parser,
        "--config",
        type=Path,
        default=None,
        help="Optional ratchetr.toml path (default: search from cwd).",
    )
    register_argument(
        parser,
        "--root",
        type=Path,
        default=None,
        help="Repository root override.",
    )
    register_argument(
        parser,
        "--ratchetr-dir",
        type=Path,
        default=None,
        help="Tool home directory override (default: <root>/.ratchetr).",
    )
    register_argument(
        parser,
        "--manifest",
        type=Path,
        default=None,
        help="Manifest path override.",
    )
    register_argument(
        parser,
        "--cache-dir",
        type=Path,
        default=None,
        help="Cache directory override.",
    )
    register_argument(
        parser,
        "--log-dir",
        type=Path,
        default=None,
        help="Log directory override.",
    )


def register_output_options(parser: ArgumentRegistrar) -> None:
    """Register global stdout/output options.

    Args:
        parser: Argument registrar to attach arguments to.
    """
    register_argument(
        parser,
        "--out",
        choices=[StdoutFormat.TEXT.value, StdoutFormat.JSON.value],
        default=StdoutFormat.TEXT.value,
        help="Stdout format for structured output (text|json).",
    )


def register_save_flag(
    parser: ArgumentRegistrar,
    *,
    flag: str,
    dest: str,
    short_flag: str | None = None,
) -> None:
    """Register a save-style flag accepting repeatable single-value arguments.

    Args:
        parser: Argument registrar to attach arguments to.
        flag: Long flag name (e.g., "--save-as").
        dest: Destination variable name in parsed namespace.
        short_flag: Optional short alias (e.g., "-s").
    """
    flags = [flag]
    if short_flag:
        flags.insert(0, short_flag)
    register_argument(
        parser,
        *flags,
        dest=dest,
        action="append",
        metavar="FORMAT[:PATH]",
        default=None,
        help="Save output in one or more formats (repeatable, each takes exactly one FORMAT[:PATH] value).",
    )


def register_readiness_flag(
    parser: ArgumentRegistrar,
    *,
    default_enabled: bool,
) -> None:
    """Register the grouped readiness token flag."""
    register_argument(
        parser,
        "--readiness",
        nargs="*",
        default=[] if default_enabled else None,
        metavar="TOKEN",
        help=READINESS_TOKENS_HELP,
    )


def build_path_overrides(args: argparse.Namespace) -> PathOverrides:
    """Create CLI path overrides from parsed args.

    Args:
        args: Parsed CLI namespace.

    Returns:
        PathOverrides: CLI-derived path overrides.
    """
    return PathOverrides(
        config_path=getattr(args, "config", None),
        repo_root=getattr(args, "root", None),
        tool_home=getattr(args, "ratchetr_dir", None),
        manifest_path=getattr(args, "manifest", None),
        cache_dir=getattr(args, "cache_dir", None),
        log_dir=getattr(args, "log_dir", None),
    )


def parse_save_flag(
    raw_values: Sequence[str] | None,
    *,
    allowed_formats: Collection[OutputFormat] | None = None,
) -> SaveFlag:
    """Parse save-style flag tokens into output targets.

    Args:
        raw_values: Raw argparse values (list of single strings) for a save-style flag.
        allowed_formats: Optional whitelist of allowed formats.

    Returns:
        SaveFlag: Parsed save flag state with any requested targets.
    """
    if raw_values is None:
        return SaveFlag(provided=False, targets=())
    if not raw_values:
        return SaveFlag(provided=True, targets=())
    targets: list[OutputTarget] = []
    for raw_value in raw_values:
        parsed = _parse_output_token(raw_value, allowed_formats=allowed_formats)
        targets.append(parsed)
    return SaveFlag(provided=True, targets=tuple(targets))


def finalise_targets(save_flag: SaveFlag, default_targets: Iterable[OutputTarget]) -> tuple[OutputTarget, ...]:
    """Return effective targets, applying defaults when the flag was provided without args.

    Args:
        save_flag: Parsed save flag output selections.
        default_targets: Targets to use when the flag was present without arguments.

    Returns:
        tuple[OutputTarget, ...]: Effective output targets in evaluation order.
    """
    if not save_flag.provided:
        return ()
    if save_flag.targets:
        return save_flag.targets
    return tuple(default_targets)


def parse_readiness_tokens(raw_tokens: Sequence[str] | None, *, flag_present: bool) -> ReadinessOptions:
    """Parse readiness tokens into typed options.

    Args:
        raw_tokens: Tokens supplied to ``--readiness``.
        flag_present: Whether the readiness flag was present on the CLI.

    Returns:
        ReadinessOptions: Parsed readiness selections.
    """
    level = ReadinessLevel.FOLDER
    limit = 10
    include_details = False
    statuses: list[ReadinessStatus] = []
    severities: list[SeverityLevel] = []
    if raw_tokens:
        for raw in raw_tokens:
            cleaned = raw.strip()
            if not cleaned:
                continue
            include_details = _update_details_flag(cleaned, include_details=include_details)
            token_key, token_value = _maybe_parse_token(cleaned)
            if token_key is None or token_value is None:
                continue
            level, limit = _apply_readiness_scalar(token_key, token_value, level, limit)
            statuses, severities = _apply_readiness_filters(token_key, token_value, statuses, severities)
    return ReadinessOptions(
        enabled=flag_present,
        level=level,
        statuses=tuple(statuses) if statuses else None,
        limit=limit,
        severities=tuple(severities) if severities else None,
        include_details=include_details,
    )


def _update_details_flag(token: str, *, include_details: bool) -> bool:
    lowered = token.lower()
    if lowered == "details":
        return True
    if lowered == "no-details":
        return False
    return include_details


def _maybe_parse_token(token: str) -> tuple[str, str] | tuple[None, None]:
    if "=" not in token:
        return (None, None)
    key, value = _split_readiness_token(token)
    return key, value


def _apply_readiness_scalar(
    key: str,
    value: str,
    level: ReadinessLevel,
    limit: int,
) -> tuple[ReadinessLevel, int]:
    if key == "level":
        return ReadinessLevel.from_str(value), limit
    if key == "limit":
        return level, _parse_positive_int(value)
    return level, limit


def _apply_readiness_filters(
    key: str,
    value: str,
    statuses: list[ReadinessStatus],
    severities: list[SeverityLevel],
) -> tuple[list[ReadinessStatus], list[SeverityLevel]]:
    if key == "status":
        status = ReadinessStatus.from_str(value)
        _append_unique(statuses, status)
        return statuses, severities
    if key == "severity":
        severity = SeverityLevel.from_str(value)
        _append_unique(severities, severity)
        return statuses, severities
    if key not in {"level", "limit"}:
        message = f"Unsupported readiness token '{key}' (expected level/status/limit/severity/details)"
        raise SystemExit(message)
    return statuses, severities


StatusT = TypeVar("StatusT", ReadinessStatus, SeverityLevel)


def _append_unique(container: list[StatusT], item: StatusT) -> None:
    if item not in container:
        container.append(item)


def _parse_output_token(
    raw_value: str,
    *,
    allowed_formats: Collection[OutputFormat] | None,
) -> OutputTarget:
    cleaned = raw_value.strip()
    if not cleaned:
        msg = "Output format cannot be empty."
        raise SystemExit(msg)
    path_part: str | None = None
    format_part = cleaned
    if ":" in cleaned:
        format_part, path_part = cleaned.split(":", 1)
        if not path_part.strip():
            msg = "Output path cannot be empty when provided."
            raise SystemExit(msg)
    try:
        fmt = OutputFormat.from_str(format_part)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    if allowed_formats is not None and fmt not in allowed_formats:
        message = (
            f"Unsupported format '{fmt.value}'. Allowed: {', '.join(sorted(fmt.value for fmt in allowed_formats))}"
        )
        raise SystemExit(message)
    path = Path(path_part) if path_part else None
    return OutputTarget(format=fmt, path=path)


def _split_readiness_token(raw: str) -> tuple[str, str]:
    if "=" not in raw:
        message = f"Invalid readiness token '{raw}'. Use key=value or boolean toggles."
        raise SystemExit(message)
    key, value = raw.split("=", 1)
    key_clean = key.strip().lower()
    value_clean = value.strip()
    if not key_clean or not value_clean:
        message = "Readiness tokens require non-empty key and value."
        raise SystemExit(message)
    return key_clean, value_clean


def _parse_positive_int(raw: str) -> int:
    try:
        parsed = int(raw)
    except ValueError as exc:
        msg = "Readiness limit must be an integer."
        raise SystemExit(msg) from exc
    if parsed < 0:
        msg = "Readiness limit must be non-negative."
        raise SystemExit(msg)
    return parsed


__all__ = [
    "READINESS_TOKENS_HELP",
    "ReadinessOptions",
    "SaveFlag",
    "StdoutFormat",
    "build_path_overrides",
    "finalise_targets",
    "parse_readiness_tokens",
    "parse_save_flag",
    "register_output_options",
    "register_path_overrides",
    "register_readiness_flag",
    "register_save_flag",
]
