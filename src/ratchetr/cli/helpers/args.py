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

# ignore JUSTIFIED: argument helpers mirror argparse signatures and allow passthrough
# typing without constraining caller kwargs; Any/ellipsis document flexible CLI
# signatures safely
# ruff: noqa: ANN401  # pylint: disable=redundant-returns-doc,unnecessary-ellipsis

"""Argument parser helpers used across CLI commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Protocol

from ratchetr.core.model_types import Mode
from ratchetr.runtime import consume

if TYPE_CHECKING:
    import argparse
    from collections.abc import Sequence


class ArgumentRegistrar(Protocol):
    """Protocol defining the interface for argument registration.

    This protocol matches the interface of argparse.ArgumentParser and argument groups,
    allowing them to be used interchangeably for adding arguments.
    """

    def add_argument(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> argparse.Action:
        """Expose ``ArgumentParser.add_argument`` so helpers can operate generically.

        Args:
            *args: Positional argument configuration passed through to ``add_argument``.
            **kwargs: Keyword options forwarded to ``add_argument``.

        Returns:
            argparse.Action: The action object created for the registered argument.
        """
        # ignore JUSTIFIED: protocol method intentionally left abstract to document
        # interface shape
        ...  # pragma: no cover


def register_argument(
    registrar: ArgumentRegistrar,
    *args: Any,
    **kwargs: Any,
) -> None:
    """Register an argument on a parser/argument group, discarding the action handle.

    Args:
        registrar: Parser or argument group on which to register the option.
        *args: Positional flags and option strings forwarded to ``add_argument``.
        **kwargs: Keyword options forwarded to ``add_argument``.
    """
    consume(registrar.add_argument(*args, **kwargs))


def parse_comma_separated(raw: str | None) -> list[str]:
    """Return a list of comma-separated values (ignoring empty entries)."""
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def parse_key_value_entries(
    entries: Sequence[str],
    *,
    argument: str,
) -> list[tuple[str, str]]:
    """Parse KEY=VALUE strings supplied via CLI flags.

    Args:
        entries: Raw CLI tokens passed to a multi-use flag.
        argument: Flag name used for constructing helpful error messages.

    Returns:
        A list of ``(key, value)`` tuples trimmed of whitespace.

    Raises:
        SystemExit: If any token omits the ``=`` separator or contains empty
            key/value content.
    """
    pairs: list[tuple[str, str]] = []
    for raw in entries:
        if "=" not in raw:
            msg = f"{argument} expects KEY=VALUE syntax"
            raise SystemExit(msg)
        key, value = raw.split("=", 1)
        key_clean = key.strip()
        value_clean = value.strip()
        if not key_clean or not value_clean:
            msg = f"{argument} expects non-empty KEY and VALUE"
            raise SystemExit(msg)
        pairs.append((key_clean, value_clean))
    return pairs


def parse_int_mapping(
    entries: Sequence[str],
    *,
    argument: str,
) -> dict[str, int]:
    """Parse KEY=INT style arguments into a mapping.

    Args:
        entries: Raw CLI tokens to interpret.
        argument: Flag name for diagnostics.

    Returns:
        Mapping of keys to non-negative integer values.

    Raises:
        SystemExit: If any value fails integer coercion.
    """
    mapping: dict[str, int] = {}
    for key, value in parse_key_value_entries(entries, argument=argument):
        try:
            budget = int(value)
        except ValueError as exc:
            msg = f"{argument} value for '{key}' must be an integer"
            raise SystemExit(msg) from exc
        mapping[key] = max(0, budget)
    return mapping


def collect_plugin_args(entries: Sequence[str]) -> dict[str, list[str]]:
    """Normalise ``--plugin-arg`` inputs into a mapping keyed by runner.

    Args:
        entries: CLI chunks formatted as ``RUNNER=ARG`` (or ``RUNNER:ARG``).

    Returns:
        Dictionary where each runner maps to a list of arguments.

    Raises:
        SystemExit: If syntax is invalid or arguments are empty.
    """
    result: dict[str, list[str]] = {}
    for raw in entries:
        if "=" in raw:
            runner, arg = raw.split("=", 1)
        elif ":" in raw:
            runner, arg = raw.split(":", 1)
        else:
            msg = f"Invalid --plugin-arg value '{raw}'. Use RUNNER=ARG (or RUNNER:ARG)."
            raise SystemExit(msg)
        runner_name = runner.strip()
        if not runner_name:
            msg = "Runner name in --plugin-arg cannot be empty"
            raise SystemExit(msg)
        arg_clean = arg.strip()
        if not arg_clean:
            msg = f"Argument for runner '{runner_name}' cannot be empty"
            raise SystemExit(msg)
        result.setdefault(runner_name, []).append(arg_clean)
    return result


def collect_profile_args(entries: Sequence[str]) -> dict[str, str]:
    """Normalise ``--profile`` overrides provided on the command line.

    Args:
        entries: CLI values provided to ``--profile``.

    Returns:
        Mapping of runner names to profile identifiers.

    Note:
        Invalid entries raise ``SystemExit`` inside ``parse_key_value_entries``.
    """
    return dict(parse_key_value_entries(entries, argument="--profile"))


def normalise_modes(values: Sequence[str] | None) -> list[Mode]:
    """Validate ``--mode`` selectors and normalise to canonical ``Mode`` values.

    Args:
        values: Raw ``--mode`` arguments, or ``None`` if not provided.

    Returns:
        Ordered list of unique ``Mode`` entries.

    Raises:
        SystemExit: If any value is not recognised as a valid mode.
    """
    if not values:
        return []
    modes: list[Mode] = []
    for raw in values:
        try:
            mode = Mode.from_str(raw)
        except ValueError as exc:
            msg = f"{exc}. Valid modes: current, full"
            raise SystemExit(msg) from exc
        if mode not in modes:
            modes.append(mode)
    return modes


def parse_hash_workers(value: str | None) -> int | Literal["auto"] | None:
    """Return a normalised hash worker spec ('auto' or non-negative integer).

    Args:
        value: CLI value supplied to ``--hash-workers``.

    Returns:
        ``None`` if no preference, ``"auto"`` for adaptive workers, or an
        integer >= 0.

    Raises:
        SystemExit: If input cannot be parsed or specifies a negative count.
    """
    if value is None:
        return None
    token = value.strip().lower()
    if not token:
        return None
    # ignore JUSTIFIED: token is a CLI mode selector, not a password or credential
    if token == "auto":  # noqa: S105
        return "auto"
    try:
        workers = int(token)
    except ValueError as exc:
        msg = "--hash-workers must be 'auto' or a non-negative integer"
        raise SystemExit(msg) from exc
    if workers < 0:
        msg = "--hash-workers must be non-negative"
        raise SystemExit(msg)
    return workers


__all__ = [
    "ArgumentRegistrar",
    "collect_plugin_args",
    "collect_profile_args",
    "normalise_modes",
    "parse_comma_separated",
    "parse_hash_workers",
    "parse_int_mapping",
    "parse_key_value_entries",
    "register_argument",
]
