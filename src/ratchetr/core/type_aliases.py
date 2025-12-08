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

"""Typed aliases used across ratchetr internals."""

from __future__ import annotations

from typing import Literal, NewType, TypeAlias

Command: TypeAlias = list[str]

PathKey = NewType("PathKey", str)
CacheKey = NewType("CacheKey", str)
CategoryName = NewType("CategoryName", str)
RuleName = NewType("RuleName", str)
ToolName = NewType("ToolName", str)
EngineName = NewType("EngineName", str)
ProfileName = NewType("ProfileName", str)
RelPath = NewType("RelPath", str)

CategoryKey = Literal["unknownChecks", "optionalChecks", "unusedSymbols", "general"]
BuiltinEngineName = Literal["pyright", "mypy"]
RunId = NewType("RunId", str)
RunnerName = EngineName

__all__ = [
    "BuiltinEngineName",
    "CacheKey",
    "CategoryKey",
    "CategoryName",
    "Command",
    "EngineName",
    "PathKey",
    "ProfileName",
    "RelPath",
    "RuleName",
    "RunId",
    "RunnerName",
    "ToolName",
]
