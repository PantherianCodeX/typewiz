# Copyright (c) 2024 PantherianCodeX

"""Utility helpers for validating and coercing loosely typed data structures."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast

from typewiz.runtime import JSONValue


def coerce_str(value: object, default: str = "") -> str:
    if isinstance(value, str):
        return value
    if value is None:
        return default
    return str(value)


def coerce_optional_str(value: object) -> str | None:
    if value is None:
        return None
    result = coerce_str(value)
    return result or None


def coerce_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default


def require_non_negative_int(value: object, *, context: str) -> int:
    result = coerce_int(value)
    if result < 0:
        message = f"{context} must be non-negative (got {result})"
        raise ValueError(message)
    return result


def coerce_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return default
    return default


def _coerce_json_value(value: object) -> JSONValue:
    if value is None:
        return None
    if isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, Mapping):
        return coerce_mapping(cast("Mapping[object, object]", value))
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        sequence_value = cast("Sequence[object]", value)
        return [_coerce_json_value(item) for item in sequence_value]
    return str(value)


def coerce_mapping(value: object) -> dict[str, JSONValue]:
    if not isinstance(value, Mapping):
        return {}
    result: dict[str, JSONValue] = {}
    value_map = cast("Mapping[object, object]", value)
    for key, item in value_map.items():
        result[str(key)] = _coerce_json_value(item)
    return result


def coerce_object_list(value: object) -> list[object]:
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        sequence_value = cast("Sequence[object]", value)
        return list(sequence_value)
    return []


def coerce_str_list(value: object) -> list[str]:
    return [coerce_str(item) for item in coerce_object_list(value)]


def coerce_optional_str_list(value: object | None) -> list[str]:
    """Coerce optional sequence-like inputs into a list of strings."""

    if value is None:
        return []
    items = coerce_object_list(value)
    result: list[str] = []
    for item in items:
        text = coerce_str(item).strip()
        if text:
            result.append(text)
    return result


def ensure_optional_str_list(value: object | None) -> list[str] | None:
    if value is None:
        return None
    result = coerce_str_list(value)
    return result or None
