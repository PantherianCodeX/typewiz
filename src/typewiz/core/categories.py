"""Category metadata used throughout Typewiz."""

from __future__ import annotations

from typing import Final, TypeGuard

from typewiz.core.type_aliases import CategoryKey, CategoryName

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
    return value in CATEGORY_KEY_SET


def coerce_category_key(value: object) -> CategoryKey | None:
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
