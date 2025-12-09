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

"""Public compatibility interface for ratchetr.

This package aggregates cross-version compatibility utilities for TOML parsing,
datetime helpers, enum extensions, and modern typing constructs. Modules that
require version-tolerant behavior should import these symbols through this
package rather than using version-specific patterns.

Re-exported symbols include:

- tomllib: Stdlib TOML parser (with a fallback to `tomli`)
- UTC: A unified timezone instance for UTC
- StrEnum: A consistent base class for string-valued enums
- Typing helpers: LiteralString, Self, TypeAliasType, override, etc.

Notes:
    - Contributors should add any new compatibility behavior to this package
      rather than scattering conditional imports throughout the codebase.
    - This module provides stable names for users and for type checkers.
"""

from __future__ import annotations

from .datetime import UTC
from .enums import StrEnum
from .toml import tomllib
from .typing import (
    LiteralString,
    Never,
    NotRequired,
    Required,
    Self,
    TypeAliasType,
    TypedDict,
    Unpack,
    assert_never,
    dataclass_transform,
    override,
)

__all__ = [
    "UTC",
    "LiteralString",
    "Never",
    "NotRequired",
    "Required",
    "Self",
    "StrEnum",
    "TypeAliasType",
    "TypedDict",
    "Unpack",
    "assert_never",
    "dataclass_transform",
    "override",
    "tomllib",
]
