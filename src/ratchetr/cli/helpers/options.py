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

"""CLI option registration and parsing utilities.

This module centralizes:

- Registration of shared CLI flags (path overrides, stdout formatting, save-style flags,
  readiness token flag).
- Parsing and normalization of user-provided tokens into typed, validated structures.
- Deterministic CLI semantics required by the CLI contract (repeatable save flags,
  explicit-vs-inferred stdout selection, readiness token grammar).

Design notes:
- Registration is intentionally factored into small helpers to keep command modules
  declarative and consistent.
- Parsing raises `SystemExit` with user-facing messages for invalid inputs, aligning
  with argparse-style error handling.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final, TypeVar

from ratchetr.cli.helpers.args import ArgumentRegistrar, register_argument
from ratchetr.compat import StrEnum, override
from ratchetr.core.model_types import ReadinessLevel, ReadinessStatus, SeverityLevel
from ratchetr.paths import OutputFormat, OutputTarget, PathOverrides

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Sequence


READINESS_TOKENS_HELP = (
    "Use key=value tokens (level=, status=, limit=, severity=) and boolean toggles (details/no-details)."
)


_OUT_EXPLICIT_ATTR: Final[str] = "_out_explicit"


class _StdoutOptionAction(argparse.Action):
    """Argparse action that tracks explicit use of `--out`.

    This action sets the destination value as usual and also marks a private attribute
    on the namespace indicating the user explicitly supplied `--out`. Downstream logic
    uses that marker to decide whether stdout format may be inferred from other flags.
    """

    @override
    def __call__(
        self,
        _parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: str | Sequence[str] | None,
        _option_string: str | None = None,
    ) -> None:
        """Store the selected stdout format and mark it as explicitly provided.

        Args:
            _parser: The argparse parser invoking this action.
            namespace: The argparse namespace to mutate.
            values: The selected stdout format token. Expected to be a string.
            _option_string: The option string used to invoke this action.
        """
        # With 'choices' restriction, values is always a string
        setattr(namespace, self.dest, values)
        setattr(namespace, _OUT_EXPLICIT_ATTR, True)


# ignore JUSTIFIED: StrEnum is Enum+str and pylint overcounts base classes.
class StdoutFormat(StrEnum):  # pylint: disable=too-many-ancestors
    """Supported stdout rendering formats.

    Values correspond to user-facing CLI tokens accepted by `--out`.
    """

    TEXT = "text"
    JSON = "json"

    @classmethod
    def from_str(cls, raw: str) -> StdoutFormat:
        """Normalize and validate a stdout format token.

        Args:
            raw: Raw token provided via CLI/configuration (case-insensitive, may include
                surrounding whitespace).

        Returns:
            The corresponding `StdoutFormat` enum value.

        Raises:
            SystemExit: If `raw` does not map to a supported format token.
        """
        token = raw.strip().lower()
        try:
            return cls(token)
        except ValueError as exc:
            message = f"Unknown output format '{raw}'"
            raise SystemExit(message) from exc


@dataclass(slots=True, frozen=True)
class SaveFlag:
    """Parsed state for a save-style CLI flag.

    Attributes:
        provided: Whether the flag was present on the CLI at all.
            - False means the flag was not provided and defaults should not be applied.
            - True means the flag was provided; if `targets` is empty, callers may apply
              command-specific defaults (see `finalise_targets`).
        targets: Parsed output targets requested by the user (may be empty when the flag
            was provided without arguments).
    """

    provided: bool
    targets: tuple[OutputTarget, ...]


@dataclass(slots=True, frozen=True)
class ReadinessOptions:
    """Parsed readiness options derived from `--readiness` tokens.

    The readiness flag supports a small token language comprised of:
    - Scalars: `level=...`, `limit=...`
    - Filters: `status=...`, `severity=...`
    - Boolean toggles: `details`, `no-details`

    Attributes:
        enabled: Whether readiness evaluation is enabled for the command invocation.
        level: Aggregation level (e.g., folder/file) used by readiness calculations.
        statuses: Optional status filter; when set, only these statuses are included.
        limit: Maximum number of entries to include in readiness output.
        severities: Optional severity filter; when set, only these severities are included.
        include_details: Whether to emit detailed readiness information.
    """

    enabled: bool
    level: ReadinessLevel
    statuses: tuple[ReadinessStatus, ...] | None
    limit: int
    severities: tuple[SeverityLevel, ...] | None
    include_details: bool


def register_path_overrides(parser: ArgumentRegistrar) -> None:
    """Register global path override flags shared across commands.

    These flags affect repository/config discovery and output locations. They are
    registered in a single place to enforce consistent CLI semantics across subcommands.

    Args:
        parser: Argument registrar used to attach arguments to the underlying parser.
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
    """Register global stdout/output formatting options.

    Currently registers `--out` (text/json). The associated action records whether
    `--out` was explicitly provided so other logic may safely infer defaults when it
    was not (see `infer_stdout_format_from_save_flag`).

    Args:
        parser: Argument registrar used to attach arguments to the underlying parser.
    """
    register_argument(
        parser,
        "--out",
        choices=[StdoutFormat.TEXT.value, StdoutFormat.JSON.value],
        default=StdoutFormat.TEXT.value,
        action=_StdoutOptionAction,
        help="Stdout format for structured output (text|json).",
    )


def register_save_flag(
    parser: ArgumentRegistrar,
    *,
    flag: str,
    dest: str,
    short_flag: str | None = None,
    aliases: Sequence[str] | None = None,
) -> None:
    """Register a save-style flag that accepts repeatable single-value arguments.

    This is the standard pattern for flags like `--save-as` / `--dashboard`, where each
    occurrence accepts exactly one token of the form `FORMAT[:PATH]` and the flag can be
    repeated to request multiple targets.

    Examples:
        - `--save-as json`
        - `--save-as json --save-as html:site/`
        - `--dashboard html:site/ --dashboard json`

    Args:
        parser: Argument registrar used to attach arguments to the underlying parser.
        flag: Long flag name (e.g., `"--save-as"`).
        dest: Attribute name on the argparse namespace to receive parsed values.
        short_flag: Optional short alias (e.g., `"-s"`).
        aliases: Optional additional long aliases (repeatable).
    """
    flags: list[str] = []
    if short_flag:
        flags.append(short_flag)
    flags.append(flag)
    if aliases:
        flags.extend(aliases)
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
    """Register the grouped readiness token flag (`--readiness`).

    The readiness flag accepts a small token language (see `READINESS_TOKENS_HELP`).
    This helper centralizes registration so all commands share identical syntax.

    Semantics:
        - When `default_enabled=True`, readiness defaults to enabled and callers may
          pass zero or more tokens.
        - When `default_enabled=False`, readiness is disabled unless the flag is
          explicitly present.

    Args:
        parser: Argument registrar used to attach arguments to the underlying parser.
        default_enabled: Whether readiness is enabled by default for the command.
    """
    register_argument(
        parser,
        "--readiness",
        nargs="*",
        default=[] if default_enabled else None,
        metavar="TOKEN",
        help=READINESS_TOKENS_HELP,
    )


def build_path_overrides(args: argparse.Namespace) -> PathOverrides:
    """Build `PathOverrides` from a parsed argparse namespace.

    This function extracts supported path override attributes (if present) and builds
    a typed `PathOverrides` object used by the path resolution layer.

    Args:
        args: Parsed argparse namespace.

    Returns:
        PathOverrides: instance populated from CLI arguments.
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
    """Parse a save-style flag into typed output targets.

    Save-style flags are repeatable and accept tokens of the form `FORMAT[:PATH]`.
    This parser provides two important pieces of state:

    - Whether the flag was present (`provided`).
    - Which targets were requested (`targets`).

    This distinction enables correct defaulting rules:
        - If the flag was *not* provided, the caller should not emit outputs.
        - If the flag was provided *without* values, the caller may apply defaults
          (see `finalise_targets`).

    Args:
        raw_values: Raw values collected by argparse (each element corresponds to one
            flag occurrence). `None` means the flag was not provided.
        allowed_formats: Optional whitelist restricting permitted output formats.

    Returns:
        SaveFlag: Describes whether the flag was provided and any parsed targets.
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


def infer_stdout_format_from_save_flag(
    args: argparse.Namespace,
    current: StdoutFormat,
    *,
    save_flag: SaveFlag | None,
) -> StdoutFormat:
    """Infer stdout format from save targets, unless `--out` was explicit.

    This function preserves user intent in the following priority order:
        1. If `--out` was explicitly provided, do not infer anything.
        2. Otherwise, if any save target requests JSON, prefer JSON stdout to keep
           stdout consistent with persisted output.
        3. Otherwise, keep the current stdout format.

    Args:
        args: Parsed argparse namespace (used to detect explicit `--out`).
        current: Current stdout format selection.
        save_flag: Parsed save flag state (or `None` if the command does not use one).

    Returns:
        StdoutFormat: The effective format after applying inference rules.
    """
    if save_flag is None or not save_flag.provided:
        return current
    if getattr(args, _OUT_EXPLICIT_ATTR, False):
        return current
    if any(target.format is OutputFormat.JSON for target in save_flag.targets):
        return StdoutFormat.JSON
    return current


def finalise_targets(save_flag: SaveFlag, default_targets: Iterable[OutputTarget]) -> tuple[OutputTarget, ...]:
    """Compute the effective output targets for a save-style flag.

    Semantics:
        - If the flag was not provided, no targets are returned.
        - If the flag was provided with explicit targets, those targets are returned.
        - If the flag was provided without values, `default_targets` are applied.

    Args:
        save_flag: Parsed save flag state.
        default_targets: Targets to apply when the flag was present without arguments.

    Returns:
        tuple[OutputTarget, ...]: The effective output targets in evaluation order.
    """
    if not save_flag.provided:
        return ()
    if save_flag.targets:
        return save_flag.targets
    return tuple(default_targets)


def parse_readiness_tokens(raw_tokens: Sequence[str] | None, *, flag_present: bool) -> ReadinessOptions:
    """Parse `--readiness` tokens into typed readiness configuration.

    Token grammar:
        - Boolean toggles:
            - `details` enables detailed output.
            - `no-details` disables detailed output.
        - Key/value tokens:
            - `level=<value>` sets readiness aggregation level.
            - `limit=<int>` sets the maximum number of entries.
            - `status=<value>` filters by readiness status (repeatable).
            - `severity=<value>` filters by severity level (repeatable).

    Unknown keys are rejected with a user-facing error.

    Args:
        raw_tokens: Raw tokens supplied to `--readiness`. May be `None`/empty.
        flag_present: Whether the flag was present on the CLI (controls `enabled`).

    Returns:
        ReadinessOptions: Describes readiness enablement and filters.
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
    """Update the details toggle based on a single token.

    Args:
        token: Token to evaluate.
        include_details: Current details state.

    Returns:
        bool: Updated flag state after applying `details` / `no-details` toggles.
    """
    lowered = token.lower()
    if lowered == "details":
        return True
    if lowered == "no-details":
        return False
    return include_details


def _maybe_parse_token(token: str) -> tuple[str, str] | tuple[None, None]:
    """Parse a key/value readiness token if it contains '='.

    Args:
        token: Candidate token.

    Returns:
        tuple(str, str) | tuple[None, None]: (key, value) when the token
            is of the form `key=value`, otherwise `(None, None)`.
    """
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
    """Apply scalar readiness tokens (`level`, `limit`) to the current state.

    Args:
        key: Token key.
        value: Token value.
        level: Current readiness level.
        limit: Current readiness limit.

    Returns:
        tuple[ReadinessLevel, int]: Updated `(level, limit)` after applying
            the scalar token (or unchanged if not applicable).
    """
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
    """Apply filter readiness tokens (`status`, `severity`) to the current lists.

    Args:
        key: Token key.
        value: Token value.
        statuses: Mutable list of selected readiness statuses.
        severities: Mutable list of selected severity levels.

    Returns:
        tuple[list[ReadinessStatus], list[SeverityLevel]]: Updated
            `(statuses, severities)` lists.

    Raises:
        SystemExit: If `key` is unsupported or `value` cannot be parsed.
    """
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
    """Append an item if it is not already present.

    Args:
        container: List to mutate.
        item: Item to append if missing.
    """
    if item not in container:
        container.append(item)


def _parse_output_token(
    raw_value: str,
    *,
    allowed_formats: Collection[OutputFormat] | None,
) -> OutputTarget:
    """Parse a single `FORMAT[:PATH]` output token into an `OutputTarget`.

    Rules:
        - `FORMAT` must be non-empty and parseable as `OutputFormat`.
        - If `:PATH` is present, `PATH` must be non-empty after stripping.
        - If `allowed_formats` is provided, `FORMAT` must be in the whitelist.

    Args:
        raw_value: Raw token from argparse.
        allowed_formats: Optional whitelist of allowed formats.

    Returns:
        OutputTarget: Contains the parsed format and optional path.

    Raises:
        SystemExit: If the token is empty, malformed, uses an unknown format, or uses
            a disallowed format.
    """
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
    """Split and normalize a readiness token of the form `key=value`.

    Args:
        raw: Raw readiness token.

    Returns:
        A `(key, value)` tuple where `key` is normalized to lowercase and stripped and
        `value` is stripped.

    Raises:
        SystemExit: If the token is not in `key=value` form or contains empty key/value.
    """
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
    """Parse a non-negative integer value from a token.

    Args:
        raw: Raw integer token value.

    Returns:
        int: Parsed integer value (guaranteed to be >= 0).

    Raises:
        SystemExit: If `raw` is not an integer or is negative.
    """
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
    "infer_stdout_format_from_save_flag",
    "parse_readiness_tokens",
    "parse_save_flag",
    "register_output_options",
    "register_path_overrides",
    "register_readiness_flag",
    "register_save_flag",
]
