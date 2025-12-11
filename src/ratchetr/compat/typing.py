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

"""Compatibility layer for modern typing features.

This module consolidates typing constructs introduced across Python 3.10-3.12
into a single import location. Features are imported from the standard library
when available, and from `typing_extensions` otherwise.

The goal is to provide strong typing without forcing callers to write version
checks or depend directly on `typing_extensions`.

Attributes:
    LiteralString
    Never
    NotRequired
    Required
    Self
    TypeAliasType
    TypedDict
    Unpack
    assert_never
    dataclass_transform
    override

Notes:
    - When type checking (`TYPE_CHECKING` is true), all names are imported
      from `typing_extensions` to give type checkers a consistent API even
      when targeting Python 3.10.
    - At runtime, stdlib versions are preferred where available, falling back
      to the backports only when necessary.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing_extensions import (
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
else:
    try:
        from typing import TypeAliasType, TypedDict, override  # py>=3.12
    except ImportError:
        from typing_extensions import TypeAliasType, TypedDict, override

    try:
        from typing import (  # py>=3.11
            LiteralString,
            Never,
            NotRequired,
            Required,
            Self,
            Unpack,
            assert_never,
            dataclass_transform,
        )
    except ImportError:  # py<3.11
        # ignore JUSTIFIED: reassign typing_extensions backports to keep the typing API
        # stable across versions
        from typing_extensions import (  # type: ignore[assignment]
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
    "LiteralString",
    "Never",
    "NotRequired",
    "Required",
    "Self",
    "TypeAliasType",
    "TypedDict",
    "Unpack",
    "assert_never",
    "dataclass_transform",
    "override",
]
