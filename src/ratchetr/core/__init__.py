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

"""Core type definitions and data structures for ratchetr.

This module provides core type definitions, enumerations, and data structures
used throughout the ratchetr type checking analysis system. It includes:

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
