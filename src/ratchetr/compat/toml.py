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

"""Compatibility layer for TOML parsing across Python versions.

This module provides a unified `tomllib` interface that works on all
supported Python versions. Python 3.11 introduced the standard-library
`tomllib` module; earlier versions require the external `tomli` package.
This shim ensures callers can always rely on an imported name called
`tomllib` without performing version checks.

Attributes:
    tomllib: A module object providing `loads()` and related TOML parsing
        utilities. On Python 3.11+, this is the stdlib module. On Python
        3.10, this is the `tomli` backport.

Notes:
    - Type checkers targeting Python 3.10 do not recognize `tomllib`.
      To prevent "missing import" errors, the module is imported from
      `tomli` under `TYPE_CHECKING`.
    - Runtime always prefers the stdlib implementation when available.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # For type checking under py310, tomllib doesn't exist, but tomli should.
    import tomli as tomllib
else:
    try:
        import tomllib  # py311+
    except ModuleNotFoundError:  # py<3.11
        import tomli as tomllib

__all__ = ["tomllib"]
