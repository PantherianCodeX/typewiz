# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

from typing import Final, cast

from .type_aliases import CategoryKey, CategoryName

CATEGORY_DISPLAY_ORDER: Final[tuple[CategoryKey, ...]] = (
    "unknownChecks",
    "optionalChecks",
    "unusedSymbols",
    "general",
)

CATEGORY_KEYS: Final[tuple[CategoryKey, ...]] = CATEGORY_DISPLAY_ORDER
CATEGORY_KEY_SET: Final[frozenset[str]] = frozenset(CATEGORY_KEYS)
CATEGORY_NAMES: Final[tuple[CategoryName, ...]] = tuple(CategoryName(key) for key in CATEGORY_KEYS)


def coerce_category_key(value: object) -> CategoryKey | None:
    token = str(value).strip()
    if not token or token not in CATEGORY_KEY_SET:
        return None
    return cast(CategoryKey, token)


__all__ = [
    "CATEGORY_DISPLAY_ORDER",
    "CATEGORY_KEYS",
    "CATEGORY_KEY_SET",
    "CATEGORY_NAMES",
    "coerce_category_key",
]
