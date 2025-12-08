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

"""Category metadata used throughout ratchetr."""

from __future__ import annotations

from typing import Final, TypeGuard

from ratchetr.core.type_aliases import CategoryKey, CategoryName

CATEGORY_DISPLAY_ORDER: Final[tuple[CategoryKey, ...]] = (
    "unknownChecks",
    "optionalChecks",
    "unusedSymbols",
    "general",
)

CATEGORY_KEYS: Final[tuple[CategoryKey, ...]] = CATEGORY_DISPLAY_ORDER
CATEGORY_KEY_SET: Final[frozenset[CategoryKey]] = frozenset(CATEGORY_KEYS)
CATEGORY_NAMES: Final[tuple[CategoryName, ...]] = tuple(CategoryName(key) for key in CATEGORY_KEYS)


def _is_category_key(value: str) -> TypeGuard[CategoryKey]:
    """Check if a string value is a valid CategoryKey.

    Args:
        value: String to check against known category keys.

    Returns:
        TypeGuard indicating if value is a valid CategoryKey.
    """
    return value in CATEGORY_KEY_SET


def coerce_category_key(value: object) -> CategoryKey | None:
    """Coerce an arbitrary object to a CategoryKey if possible.

    Converts the value to a string, strips whitespace, and validates it
    against known category keys. Returns None if the value cannot be
    coerced to a valid CategoryKey.

    Args:
        value: Arbitrary object to coerce to a CategoryKey.

    Returns:
        Valid CategoryKey if coercion succeeds, None otherwise.
    """
    token = str(value).strip()
    if not token or not _is_category_key(token):
        return None
    return token


__all__ = [
    "CATEGORY_DISPLAY_ORDER",
    "CATEGORY_KEYS",
    "CATEGORY_KEY_SET",
    "CATEGORY_NAMES",
    "coerce_category_key",
]
