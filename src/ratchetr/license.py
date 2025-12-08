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

"""License helpers provided for CLI and packaging layers."""

from __future__ import annotations

from ratchetr._internal.license import (
    LICENSE_KEY_ENV,
    has_commercial_license,
    license_mode,
    maybe_emit_evaluation_notice,
)

__all__ = [
    "LICENSE_KEY_ENV",
    "has_commercial_license",
    "license_mode",
    "maybe_emit_evaluation_notice",
]
