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

"""CLI package for ratchetr."""

from __future__ import annotations

from .app import main, write_config_template
from .helpers.formatting import (
    SUMMARY_FIELD_CHOICES,
    print_readiness_summary,
    print_summary,
    query_readiness,
)

try:  # pragma: no cover - defensive import guard
    from ratchetr import __version__ as _pkg_version
except Exception:  # pragma: no cover  # noqa: BLE001 JUSTIFIED: fallback for partial initialisation
    _pkg_version = "0.0.0"

__version__ = _pkg_version

__all__ = [
    "SUMMARY_FIELD_CHOICES",
    "__version__",
    "main",
    "print_readiness_summary",
    "print_summary",
    "query_readiness",
    "write_config_template",
]
