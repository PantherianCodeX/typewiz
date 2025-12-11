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

"""Command modules for the ratchetr CLI."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from types import ModuleType

_EXPORTED_MODULES: Final[tuple[str, ...]] = ("audit", "cache", "engines", "help", "manifest", "query", "ratchet")
# ignore JUSTIFIED: dynamic CLI submodule re-export; dunder-all is populated from a
# fixed tuple of module names
__all__ = list(_EXPORTED_MODULES)  # pyright: ignore[reportUnsupportedDunderAll]


def __getattr__(name: str) -> ModuleType:
    if name not in _EXPORTED_MODULES:
        message = f"module '{__name__}' has no attribute '{name}'"
        raise AttributeError(message)
    module = importlib.import_module(f"{__name__}.{name}")
    globals()[name] = module
    return module


def __dir__() -> list[str]:
    return sorted(_EXPORTED_MODULES)
