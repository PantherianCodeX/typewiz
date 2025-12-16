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

"""Canonical JSON types and helpers used across ratchetr.

This module defines the JSON value shapes and generic helpers for working
with JSON-compatible data. It intentionally has no dependencies on
logging, configuration, or CLI layers to keep the dependency graph
simple and acyclic.
"""

from __future__ import annotations

import json
from enum import Enum
from typing import TypeAlias, cast

from pydantic import JsonValue

__all__ = [
    "JSONList",
    "JSONMapping",
    "JSONValue",
    "as_int",
    "as_list",
    "as_mapping",
    "as_str",
    "normalize_enums_for_json",
    "require_json",
]

JSONValue: TypeAlias = JsonValue
JSONMapping = dict[str, JsonValue]
JSONList = list[JsonValue]


def require_json(payload: str, fallback: str | None = None) -> JSONMapping:
    """Parse a JSON string into a mapping, with basic validation.

    Args:
        payload: Raw JSON string to parse.
        fallback: Optional fallback string to use when `payload` is empty.

    Returns:
        Parsed JSON object as a string-keyed mapping.

    Raises:
        ValueError: If both `payload` and `fallback` are empty.
    """
    if not (data_str := payload.strip() or fallback or ""):
        message = "Expected JSON output but received empty string"
        raise ValueError(message)
    return cast("JSONMapping", json.loads(data_str))


def as_mapping(value: object) -> JSONMapping:
    """Return `value` as a JSON mapping if it is a dict, else an empty mapping.

    Args:
        value: Arbitrary value to convert.

    Returns:
        A `dict` when `value` is already a mapping, otherwise an empty mapping.
    """
    return cast("JSONMapping", value) if isinstance(value, dict) else {}


def as_list(value: object) -> JSONList:
    """Return `value` as a JSON list if it is a list, else an empty list.

    Args:
        value: Arbitrary value to convert.

    Returns:
        A `list` when `value` is already a list, otherwise an empty list.
    """
    return cast("JSONList", value) if isinstance(value, list) else []


def as_str(value: object, default: str = "") -> str:
    """Return `value` as a string if already a string, else `default`.

    Args:
        value: Arbitrary value to convert.
        default: Fallback string to return when `value` is not a string.

    Returns:
        The original string value or the `default` fallback.
    """
    if isinstance(value, str):
        return value
    return default


def as_int(value: object, default: int = 0) -> int:
    """Return `value` as an int when possible, else `default`.

    Args:
        value: Arbitrary value to convert.
        default: Fallback integer to return when conversion is not possible.

    Returns:
        The integer representation of `value` or the `default` fallback.
    """
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def normalize_enums_for_json(value: object) -> JSONValue:
    """Recursively convert Enum keys/values to their string payloads for JSON serialisation.

    Args:
        value: Arbitrary Python object hierarchy that may include `Enum`
            instances, mappings, or sequences.

    Returns:
        A JSON-compatible structure (built from `dict`/`list`/primitives)
        with all enum keys and values replaced by their `.value` payloads.
    """

    def _convert(obj: object) -> JSONValue:
        if isinstance(obj, Enum):
            return cast("JSONValue", obj.value)
        if isinstance(obj, dict):
            mapping_obj = cast("dict[object, object]", obj)
            result: dict[str, JSONValue] = {}
            for key, raw_val in mapping_obj.items():
                if isinstance(key, Enum):
                    norm_key: str = str(key.value)
                elif isinstance(key, str):
                    norm_key = key
                else:
                    norm_key = str(key)
                result[norm_key] = _convert(raw_val)
            return cast("JSONValue", result)
        if isinstance(obj, list):
            list_obj = cast("list[object]", obj)
            return cast("JSONValue", [_convert(item) for item in list_obj])
        if isinstance(obj, tuple):
            tuple_obj = cast("tuple[object, ...]", obj)
            return cast("JSONValue", [_convert(item) for item in tuple_obj])
        if isinstance(obj, (str, int, float, bool)) or obj is None:
            return cast("JSONValue", obj)
        return cast("JSONValue", str(obj))

    return _convert(value)
