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

"""s11r2 progress roll-up + dashboard generator (library).

The CLI entrypoint is `scripts/docs/s11r2-progress.py`.

This package is intentionally small and self-contained so it can be executed in
minimal environments while still remaining strongly typed and lint-friendly.
"""

from __future__ import annotations

from scripts.docs.s11r2_progress.cli import main

__all__ = ["main"]
