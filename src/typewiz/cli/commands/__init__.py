# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Command modules for the typewiz CLI."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from types import ModuleType

_EXPORTED_MODULES: Final[tuple[str, ...]] = ("audit", "cache", "engines", "help", "manifest", "query", "ratchet")
__all__ = list(_EXPORTED_MODULES)  # pyright: ignore[reportUnsupportedDunderAll]  # JUSTIFIED: dynamic CLI submodule re-export; module names are statically enumerated


def __getattr__(name: str) -> ModuleType:
    if name not in _EXPORTED_MODULES:
        message = f"module '{__name__}' has no attribute '{name}'"
        raise AttributeError(message)
    module = importlib.import_module(f"{__name__}.{name}")
    globals()[name] = module
    return module


def __dir__() -> list[str]:
    return sorted(_EXPORTED_MODULES)
