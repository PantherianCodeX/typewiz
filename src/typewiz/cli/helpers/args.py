# Copyright (c) 2024 PantherianCodeX
"""Argument parser helpers used across CLI commands."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import Any, Protocol

from typewiz.model_types import Mode
from typewiz.utils import consume


class ArgumentRegistrar(Protocol):
    def add_argument(
        self, *args: Any, **kwargs: Any
    ) -> argparse.Action: ...  # pragma: no cover - stub


def register_argument(
    registrar: ArgumentRegistrar,
    *args: Any,
    **kwargs: Any,
) -> None:
    """Register an argument on a parser/argument group, discarding the action handle."""
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
    """Parse KEY=VALUE strings supplied via CLI flags."""
    pairs: list[tuple[str, str]] = []
    for raw in entries:
        if "=" not in raw:
            raise SystemExit(f"{argument} expects KEY=VALUE syntax")
        key, value = raw.split("=", 1)
        key_clean = key.strip()
        value_clean = value.strip()
        if not key_clean or not value_clean:
            raise SystemExit(f"{argument} expects non-empty KEY and VALUE")
        pairs.append((key_clean, value_clean))
    return pairs


def parse_int_mapping(
    entries: Sequence[str],
    *,
    argument: str,
) -> dict[str, int]:
    """Parse KEY=INT style arguments into a mapping."""
    mapping: dict[str, int] = {}
    for key, value in parse_key_value_entries(entries, argument=argument):
        try:
            budget = int(value)
        except ValueError as exc:
            raise SystemExit(f"{argument} value for '{key}' must be an integer") from exc
        mapping[key] = max(0, budget)
    return mapping


def collect_plugin_args(entries: Sequence[str]) -> dict[str, list[str]]:
    """Normalise ``--plugin-arg`` inputs into a mapping keyed by runner."""
    result: dict[str, list[str]] = {}
    for raw in entries:
        if "=" in raw:
            runner, arg = raw.split("=", 1)
        elif ":" in raw:
            runner, arg = raw.split(":", 1)
        else:
            raise SystemExit(f"Invalid --plugin-arg value '{raw}'. Use RUNNER=ARG (or RUNNER:ARG).")
        runner_name = runner.strip()
        if not runner_name:
            raise SystemExit("Runner name in --plugin-arg cannot be empty")
        arg_clean = arg.strip()
        if not arg_clean:
            raise SystemExit(f"Argument for runner '{runner_name}' cannot be empty")
        result.setdefault(runner_name, []).append(arg_clean)
    return result


def collect_profile_args(entries: Sequence[str]) -> dict[str, str]:
    """Normalise ``--profile`` overrides provided on the command line."""
    return {
        runner: profile
        for runner, profile in parse_key_value_entries(entries, argument="--profile")
    }


def normalise_modes(values: Sequence[str] | None) -> list[Mode]:
    """Validate ``--mode`` selectors and normalise to canonical ``Mode`` values."""
    if not values:
        return []
    modes: list[Mode] = []
    for raw in values:
        try:
            mode = Mode.from_str(raw)
        except ValueError as exc:
            raise SystemExit(f"{exc}. Valid modes: current, full") from exc
        if mode not in modes:
            modes.append(mode)
    return modes


__all__ = [
    "ArgumentRegistrar",
    "collect_plugin_args",
    "collect_profile_args",
    "normalise_modes",
    "parse_comma_separated",
    "parse_int_mapping",
    "parse_key_value_entries",
    "register_argument",
]
