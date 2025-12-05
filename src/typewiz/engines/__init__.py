# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Type checker engine abstraction and registry for TypeWiz.

This module provides the core engine interfaces and utilities for running type
checkers like mypy and pyright. It exports the base engine protocol, configuration
classes, and the engine resolution mechanism for discovering and loading engines.

The main entry point for working with engines is the `resolve_engines` function,
which discovers both builtin and plugin-provided type checker engines.
"""

from .base import BaseEngine, EngineContext, EngineOptions, EngineResult
from .registry import resolve_engines

__all__ = [
    "BaseEngine",
    "EngineContext",
    "EngineOptions",
    "EngineResult",
    "resolve_engines",
]
