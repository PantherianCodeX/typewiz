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

"""Compatibility helpers for string-valued enums.

Python 3.11 introduced `enum.StrEnum`, a convenient base class for enums whose
values are strings. Python 3.10 does not provide this class. This module
exposes a `StrEnum` symbol that maps to the stdlib version when available,
or a lightweight backport otherwise.

Classes:
    StrEnum: A base class for enums with string values. On Python 3.11+ this
        is the stdlib `enum.StrEnum`. On Python 3.10 it is a compatible
        fallback that derives from both `str` and `Enum`.

Notes:
    - Centralizing the fallback here prevents version-specific imports in
      other modules.
    - The backport behaves consistently with the stdlib for typical
      ratchetr use cases.
"""

from __future__ import annotations

import enum as _enum
from typing import TYPE_CHECKING, cast

from ratchetr.compat.typing import override


class _StrEnumBase(str, _enum.Enum):
    """Type base for StrEnum-like enums."""


if TYPE_CHECKING:

    class StrEnum(_StrEnumBase):
        """Type-checker view of StrEnum."""

        @override
        def __str__(self) -> str:
            """Return the enum member's value, matching stdlib StrEnum."""
            # ignore JUSTIFIED: TYPE_CHECKING-only stub mirrors stdlib StrEnum; runtime
            # logic lives in the else-branch
            ...  # pragma: no cover  # pylint: disable=unnecessary-ellipsis

else:
    _STR_ENUM = getattr(_enum, "StrEnum", None)

    if _STR_ENUM is None:

        class _CompatStrEnum(_StrEnumBase):
            """Backport of enum.StrEnum for Python 3.10."""

            @override
            def __str__(self) -> str:
                """Return the enum member's value, matching stdlib StrEnum."""
                return str(self.value)

        StrEnum: type[_StrEnumBase] = _CompatStrEnum
    else:
        StrEnum = cast("type[_StrEnumBase]", _STR_ENUM)

__all__ = ["StrEnum"]
