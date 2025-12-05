# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Readiness assessment module for analyzing type coverage and code quality.

This module provides functionality for computing and viewing readiness metrics
that help assess how close code is to being fully typed and production-ready.
"""

from __future__ import annotations

from .compute import (
    CATEGORY_CLOSE_THRESHOLD,
    CATEGORY_LABELS,
    CATEGORY_PATTERNS,
    DEFAULT_CLOSE_THRESHOLD,
    GENERAL_CATEGORY,
    STRICT_CLOSE_THRESHOLD,
    ReadinessEntry,
    ReadinessOptions,
    ReadinessPayload,
    compute_readiness,
)
from .views import (
    FileReadinessPayload,
    FolderReadinessPayload,
    ReadinessValidationError,
    ReadinessViewResult,
    collect_readiness_view,
)

__all__ = [
    "CATEGORY_CLOSE_THRESHOLD",
    "CATEGORY_LABELS",
    "CATEGORY_PATTERNS",
    "DEFAULT_CLOSE_THRESHOLD",
    "GENERAL_CATEGORY",
    "STRICT_CLOSE_THRESHOLD",
    "FileReadinessPayload",
    "FolderReadinessPayload",
    "ReadinessEntry",
    "ReadinessOptions",
    "ReadinessPayload",
    "ReadinessValidationError",
    "ReadinessViewResult",
    "collect_readiness_view",
    "compute_readiness",
]
