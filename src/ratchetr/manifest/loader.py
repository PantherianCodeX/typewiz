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

"""Load and validate manifest data from raw input.

This module provides utilities for loading manifest data from arbitrary
sources (typically JSON files) and validating them against the manifest schema.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .models import validate_manifest_payload

if TYPE_CHECKING:
    from .typed import ManifestData


def load_manifest_data(raw: Any) -> ManifestData:  # noqa: ANN401  # JUSTIFIED: Accepts arbitrary input from JSON parsing, validated at runtime
    """Parse manifest payloads using strict validation.

    Args:
        raw: Raw manifest data from any source (typically parsed JSON).

    Returns:
        Validated ManifestData TypedDict.
    """
    return validate_manifest_payload(raw)
