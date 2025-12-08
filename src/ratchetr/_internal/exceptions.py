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

"""Common exception hierarchy for ratchetr."""

from __future__ import annotations

__all__ = ["RatchetrError", "RatchetrTypeError", "RatchetrValidationError"]


class RatchetrError(Exception):
    """Base error for all ratchetr exceptions."""


class RatchetrValidationError(RatchetrError, ValueError):
    """Raised when input data fails validation checks."""


class RatchetrTypeError(RatchetrError, TypeError):
    """Raised when input data has an unexpected type."""
