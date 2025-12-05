# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Core type definitions and data structures for Typewiz.

This module provides core type definitions, enumerations, and data structures
used throughout the Typewiz type checking analysis system. It includes:

- Model types: Enums for modes, severities, status values, and formats
- Summary types: TypedDict definitions for summary and dashboard data
- Type aliases: Common type aliases used across the codebase
- Core types: Dataclasses for diagnostics and run results
- Categories: Category metadata and utilities
"""

from __future__ import annotations

from . import categories, model_types, summary_types, type_aliases, types

__all__ = [
    "categories",
    "model_types",
    "summary_types",
    "type_aliases",
    "types",
]
