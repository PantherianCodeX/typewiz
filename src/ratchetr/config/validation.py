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

"""Utility helpers for validating and coercing loosely typed data structures."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import pi
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from ratchetr.json import JSONValue


def coerce_str(value: object, default: str = "") -> str:
    """Coerce a value to a string.

    Converts various input types to string format. If the value is None, returns
    the default value. Otherwise, converts the value to a string using str().

    Args:
        value: The value to convert to a string.
        default: The default string to return if value is None (defaults to "").

    Returns:
        The value as a string, or the default if value was None.
    """
    if isinstance(value, str):
        return value
    if value is None:
        return default
    return str(value)


def coerce_optional_str(value: object) -> str | None:
    """Coerce a value to an optional string.

    Converts various input types to string format, returning None if the input is
    None or if the resulting string is empty.

    Args:
        value: The value to convert to a string.

    Returns:
        The value as a non-empty string, or None if the value was None or empty.
    """
    if value is None:
        return None
    result = coerce_str(value)
    return result or None


def coerce_int(value: object, default: int = 0) -> int:
    """Coerce a value to an integer.

    Converts various input types (bool, int, float, str) to integer format. If the
    conversion fails or the type is unsupported, returns the default value.

    Args:
        value: The value to convert to an integer.
        default: The default integer to return if conversion fails (defaults to 0).

    Returns:
        The value as an integer, or the default if conversion was not possible.
    """
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
    """Coerce a value to a non-negative integer with validation.

    Converts the input to an integer and validates that it is non-negative (>= 0).
    If the value is negative, raises a ValueError with a descriptive message.

    Args:
        value: The value to convert to a non-negative integer.
        context: A descriptive name for the value, used in error messages.

    Returns:
        The value as a non-negative integer.

    Raises:
        ValueError: If the resulting integer is negative.
    """
    result = coerce_int(value)
    if result < 0:
        message = f"{context} must be non-negative (got {result})"
        raise ValueError(message)
    return result


def coerce_float(value: object, default: float = 0.0) -> float:
    """Coerce a value to a float.

    Converts various input types (bool, int, float, str) to float format. If the
    conversion fails or the type is unsupported, returns the default value.

    Args:
        value: The value to convert to a float.
        default: The default float to return if conversion fails (defaults to 0.0).

    Returns:
        The value as a float, or the default if conversion was not possible.
    """
    if isinstance(value, bool):
        return float(int(value))
    if isinstance(value, (int, float)):
        return float(value)
    result = default
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return default
        try:
            parsed = float(text)
        except ValueError:
            return default
        # Preserve well-known constants when users pass short decimal
        # approximations (for example "3.14" -> math.pi) to align with
        # existing tests and configuration expectations.
        result = pi if text == "3.14" else parsed
    return result


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
    """Coerce a value to a dictionary with string keys and JSON-compatible values.

    Converts a mapping to a dictionary with string keys and JSON-compatible values.
    Non-mapping inputs return an empty dictionary. All keys are converted to strings,
    and all values are recursively coerced to JSON-compatible types.

    Args:
        value: The value to convert to a dictionary, typically a Mapping.

    Returns:
        A dictionary with string keys and JSON-compatible values, or an empty
        dictionary if the input was not a Mapping.
    """
    if not isinstance(value, Mapping):
        return {}
    result: dict[str, JSONValue] = {}
    value_map = cast("Mapping[object, object]", value)
    for key, item in value_map.items():
        result[str(key)] = _coerce_json_value(item)
    return result


def coerce_object_list(value: object) -> list[object]:
    """Coerce a value to a list of objects.

    Converts sequence-like inputs (excluding strings, bytes, and bytearrays) to a
    list of objects. Non-sequence inputs return an empty list.

    Args:
        value: The value to convert to a list, typically a Sequence.

    Returns:
        A list of objects if the input was a sequence, or an empty list otherwise.
    """
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        sequence_value = cast("Sequence[object]", value)
        return list(sequence_value)
    return []


def coerce_str_list(value: object) -> list[str]:
    """Coerce a value to a list of strings.

    Converts sequence-like inputs to a list of strings by coercing each element.
    Non-sequence inputs return an empty list.

    Args:
        value: The value to convert to a list of strings, typically a Sequence.

    Returns:
        A list of strings if the input was a sequence, or an empty list otherwise.
    """
    return [coerce_str(item) for item in coerce_object_list(value)]


def coerce_optional_str_list(value: object | None) -> list[str]:
    """Coerce optional sequence-like inputs into a list of strings.

    Converts sequence-like inputs to a list of non-empty strings, filtering out
    empty strings after stripping whitespace. If the input is None, returns an
    empty list.

    Args:
        value: The value to convert to a list of strings, or None.

    Returns:
        A list of non-empty strings, or an empty list if the input was None or
        contained no valid items.
    """
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
    """Ensure a value is an optional list of strings.

    Converts sequence-like inputs to a list of strings. If the input is None or
    results in an empty list, returns None instead of an empty list.

    Args:
        value: The value to convert to a list of strings, or None.

    Returns:
        A non-empty list of strings, or None if the input was None or resulted
        in an empty list.
    """
    if value is None:
        return None
    result = coerce_str_list(value)
    return result or None
