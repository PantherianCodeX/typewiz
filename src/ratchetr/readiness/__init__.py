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
