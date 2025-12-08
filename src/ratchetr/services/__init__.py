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

"""Service layer orchestrating high-level audit, dashboard, manifest, ratchet, and readiness operations.

This module provides a clean API boundary between the CLI/application layers
and the core business logic. Each submodule encapsulates workflows that combine
multiple lower-level components to perform complete operations like running
audits, validating manifests, updating ratchets, and generating dashboards.
"""

from __future__ import annotations

from . import audit, dashboard, manifest, ratchet, readiness

__all__ = ["audit", "dashboard", "manifest", "ratchet", "readiness"]
