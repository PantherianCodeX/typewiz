"""Pure helper utilities used by the CLI command implementations."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Literal, cast

from .data_validation import coerce_mapping
from .formatting import render_table_rows, stringify
from .utils import JSONValue

__all__ = [
    "collect_plugin_args",
    "collect_profile_args",
    "format_list",
    "normalise_modes",
    "parse_summary_fields",
    "render_data_structure",
]


def format_list(values: Sequence[str]) -> str:
    """Return a comma-separated string for CLI presentation."""

    return ", ".join(values) if values else "—"


def parse_summary_fields(raw: str | None, *, valid_fields: set[str]) -> list[str]:
    """Parse ``--summary-fields`` input, validating against ``valid_fields``."""

    if not raw:
        return []
    fields: list[str] = []
    for part in raw.split(","):
        item = part.strip().lower()
        if not item:
            continue
        if item == "all":
            return sorted(valid_fields)
        if item not in valid_fields:
            message = (
                f"Unknown summary field '{item}'. "
                f"Valid values: {', '.join(sorted(valid_fields | {'all'}))}"
            )
            raise SystemExit(message)
        if item not in fields:
            fields.append(item)
    return fields


def render_data_structure(data: object, fmt: Literal["json", "table"]) -> list[str]:
    """Render a Python object for CLI output in the requested format."""

    if fmt == "json":
        return [json.dumps(data, indent=2, ensure_ascii=False)]
    if isinstance(data, list):
        table_rows: list[Mapping[str, JSONValue]] = []
        for item_obj in cast(list[object], data):
            if isinstance(item_obj, Mapping):
                mapping_item = cast(Mapping[object, object], item_obj)
                table_rows.append(coerce_mapping(mapping_item))
        return render_table_rows(table_rows)
    if isinstance(data, Mapping):
        mapping_data = coerce_mapping(cast(Mapping[object, object], data))
        dict_rows: list[Mapping[str, JSONValue]] = [
            {"key": str(key), "value": value} for key, value in mapping_data.items()
        ]
        return render_table_rows(dict_rows)
    return [stringify(data)]


def collect_plugin_args(entries: Sequence[str]) -> dict[str, list[str]]:
    """Normalise ``--plugin-arg``/``--profile`` CLI inputs into a mapping."""

    result: dict[str, list[str]] = {}
    for raw in entries:
        if "=" in raw:
            runner, arg = raw.split("=", 1)
        elif ":" in raw:
            runner, arg = raw.split(":", 1)
        else:
            message = f"Invalid --plugin-arg value '{raw}'. Use RUNNER=ARG (or RUNNER:ARG)."
            raise SystemExit(message)
        runner = runner.strip()
        if not runner:
            message = "Runner name in --plugin-arg cannot be empty"
            raise SystemExit(message)
        arg_clean = arg.strip()
        if not arg_clean:
            message = f"Argument for runner '{runner}' cannot be empty"
            raise SystemExit(message)
        result.setdefault(runner, []).append(arg_clean)
    return result


def collect_profile_args(entries: Sequence[str]) -> dict[str, str]:
    """Normalise ``--profile`` overrides provided on the command line."""

    result: dict[str, str] = {}
    for raw in entries:
        if "=" not in raw:
            message = "--profile expects RUNNER=PROFILE syntax"
            raise SystemExit(message)
        runner, profile = raw.split("=", 1)
        runner = runner.strip()
        profile = profile.strip()
        if not runner or not profile:
            message = "--profile expects RUNNER=PROFILE syntax"
            raise SystemExit(message)
        result[runner] = profile
    return result


def normalise_modes(values: Sequence[str] | None) -> list[str]:
    """Validate ``--mode`` selectors and normalise to canonical forms."""

    if not values:
        return []
    modes: list[str] = []
    for raw in values:
        item = raw.strip().lower()
        if item not in {"current", "full"}:
            message = f"Unknown mode '{item}'. Valid modes: current, full"
            raise SystemExit(message)
        if item not in modes:
            modes.append(item)
    return modes
