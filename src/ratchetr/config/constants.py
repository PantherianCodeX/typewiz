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

"""Shared configuration defaults for ratchetr paths."""

from __future__ import annotations

from typing import Final

DEFAULT_TOOL_HOME_DIRNAME: Final[str] = ".ratchetr"
DEFAULT_CACHE_DIRNAME: Final[str] = ".cache"
DEFAULT_LOG_DIRNAME: Final[str] = "logs"
DEFAULT_MANIFEST_FILENAME: Final[str] = "manifest.json"
DEFAULT_DASHBOARD_FILENAME: Final[str] = "dashboard.html"

__all__ = [
    "DEFAULT_CACHE_DIRNAME",
    "DEFAULT_DASHBOARD_FILENAME",
    "DEFAULT_LOG_DIRNAME",
    "DEFAULT_MANIFEST_FILENAME",
    "DEFAULT_TOOL_HOME_DIRNAME",
]
