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

"""Type checker engine abstraction and registry for ratchetr.

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
