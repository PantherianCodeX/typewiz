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

"""Compatibility helpers for timezone handling.

This module exposes a single cross-version `UTC` object. Python 3.11
introduced `datetime.UTC` as the canonical timezone instance. Earlier
versions use `datetime.timezone.utc`. This shim normalizes the difference.

Attributes:
    UTC (tzinfo): A timezone object representing Coordinated Universal Time.
        On Python 3.11+, this is `datetime.UTC`. On earlier versions,
        this is `datetime.timezone.utc`.

Notes:
    Using this module avoids conditional imports like `from datetime import UTC`,
    which do not exist on Python 3.10 and would cause type-checker errors.
"""

from __future__ import annotations

import datetime as _dt
from datetime import timezone as _timezone

UTC = getattr(_dt, "UTC", _timezone.utc)

__all__ = ["UTC"]
