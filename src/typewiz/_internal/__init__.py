# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Private infrastructure modules for Typewiz internals."""

from __future__ import annotations

import importlib
from types import ModuleType

__all__ = [
    "cache",
    "collection_utils",
    "error_codes",
    "exceptions",
    "license",
    "logging_utils",
    "utils",
]

cache: ModuleType
collection_utils: ModuleType
error_codes: ModuleType
exceptions: ModuleType
license: ModuleType
logging_utils: ModuleType
utils: ModuleType


def __getattr__(name: str) -> ModuleType:
    if name not in __all__:
        message = f"module 'typewiz._internal' has no attribute '{name}'"
        raise AttributeError(message)
    module = importlib.import_module(f"{__name__}.{name}")
    globals()[name] = module
    return module


def __dir__() -> list[str]:
    return sorted(__all__)
