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

"""Private infrastructure modules for ratchetr internals."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from types import ModuleType

    cache: ModuleType
    collection_utils: ModuleType
    error_codes: ModuleType
    exceptions: ModuleType
    logging_utils: ModuleType
    utils: ModuleType

_EXPOSED_MODULES: Final[tuple[str, ...]] = (
    "cache",
    "collection_utils",
    "error_codes",
    "exceptions",
    "logging_utils",
    "utils",
)
# ignore JUSTIFIED: dynamic re-export module; dunder-all is derived from a fixed
# tuple of internal module names
__all__ = list(_EXPOSED_MODULES)  # pyright: ignore[reportUnsupportedDunderAll]


def __getattr__(name: str) -> ModuleType:
    if name not in _EXPOSED_MODULES:
        message = f"module 'ratchetr._infra' has no attribute '{name}'"
        raise AttributeError(message)
    module = importlib.import_module(f"{__name__}.{name}")
    globals()[name] = module
    return module


def __dir__() -> list[str]:
    return sorted(_EXPOSED_MODULES)
