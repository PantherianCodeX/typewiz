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

"""Compatibility shims for Python 3.10+ (and type-checker-friendly imports).

Design goals:
- Runtime works on 3.10-3.13 without users needing to think about it.
- Type checkers (pyright/mypy) don't get confused by version branching.
- Prefer stdlib when present; fall back to well-supported backports.

Deps (pyproject markers shown below):
- typing_extensions (for py<3.12)
- tomli (for py<3.11)
"""

from __future__ import annotations

import datetime as _dt
import enum as _enum
from datetime import timezone as _timezone
from typing import TYPE_CHECKING, cast

# ------------------------------------------------------------
# TOML: tomllib (3.11+) / tomli (<=3.10)
#
# IMPORTANT:
# - "import tomllib" will be flagged by pyright when pythonVersion=3.10
# - so we use TYPE_CHECKING to import a resolvable module for analysis
# ------------------------------------------------------------
if TYPE_CHECKING:
    # For type checking under py310, tomllib doesn't exist, but tomli should.
    # Ensure you have: tomli; python_version < "3.11"
    import tomli as tomllib
else:
    try:
        import tomllib  # py311+
    except ModuleNotFoundError:
        import tomli as tomllib


# ------------------------------------------------------------
# datetime.UTC (3.11+) fallback
# Avoid "from datetime import UTC" (pyright will flag on py310 target)
# ------------------------------------------------------------
UTC = getattr(_dt, "UTC", _timezone.utc)


# ------------------------------------------------------------
# enum.StrEnum (3.11+) fallback
# Avoid "from enum import StrEnum" (pyright will flag on py310 target)
# ------------------------------------------------------------
class _StrEnumBase(str, _enum.Enum):
    """Type base for StrEnum-like enums."""


_StrEnum = getattr(_enum, "StrEnum", None)

if _StrEnum is None:

    class _CompatStrEnum(_StrEnumBase):
        """Backport of enum.StrEnum for Python 3.10."""

    StrEnum: type[_StrEnumBase] = _CompatStrEnum
else:
    # enum.StrEnum exists at runtime (3.11+), but we must obtain it safely.
    StrEnum: type[_StrEnumBase] = cast("type[_StrEnumBase]", _StrEnum)


# ------------------------------------------------------------
# Typing features: prefer stdlib when present, otherwise typing_extensions.
# TYPE_CHECKING makes pyright happy while still preferring stdlib at runtime.
# ------------------------------------------------------------
if TYPE_CHECKING:
    from typing_extensions import (
        LiteralString,
        Never,
        NotRequired,
        Required,
        Self,
        TypeAliasType,
        TypedDict,  # noqa: TC004  # JUSTIFIED: for py310 type checking
        Unpack,
        assert_never,
        dataclass_transform,
        override,
    )
else:
    # ---- Python 3.12 ----
    try:
        from typing import TypeAliasType, override
    except ImportError:  # py<3.12
        from typing_extensions import TypeAliasType, override

    # ---- Python 3.11 ----
    try:
        from typing import (
            LiteralString,
            Never,
            NotRequired,
            Required,
            Self,
            Unpack,
            assert_never,
            dataclass_transform,
        )

    # ---- Python 3.10 ----
    except ImportError:
        from typing_extensions import (
            LiteralString,
            Never,
            NotRequired,
            Required,
            Self,
            Unpack,
            assert_never,
            dataclass_transform,
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
