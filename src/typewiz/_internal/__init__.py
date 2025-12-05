# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Private infrastructure modules for Typewiz internals."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from types import ModuleType

    cache: ModuleType
    collection_utils: ModuleType
    error_codes: ModuleType
    exceptions: ModuleType
    license: ModuleType  # noqa: A001  # JUSTIFIED: module attribute name must match public API typewiz._internal.license
    logging_utils: ModuleType
    utils: ModuleType

_EXPOSED_MODULES: Final[tuple[str, ...]] = (
    "cache",
    "collection_utils",
    "error_codes",
    "exceptions",
    "license",
    "logging_utils",
    "utils",
)
__all__ = list(_EXPOSED_MODULES)  # pyright: ignore[reportUnsupportedDunderAll]  # JUSTIFIED: dynamic re-export module; exports are fully enumerated and stable


def __getattr__(name: str) -> ModuleType:
    if name not in _EXPOSED_MODULES:
        message = f"module 'typewiz._internal' has no attribute '{name}'"
        raise AttributeError(message)
    module = importlib.import_module(f"{__name__}.{name}")
    globals()[name] = module
    return module


def __dir__() -> list[str]:
    return sorted(_EXPOSED_MODULES)
