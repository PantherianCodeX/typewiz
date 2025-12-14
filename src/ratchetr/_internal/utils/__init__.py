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

"""Structured utility helpers used across ratchetr internals."""

from __future__ import annotations

from .common import consume
from .locks import file_lock
from .paths import ROOT_MARKERS, RootMarker, resolve_project_root
from .process import CommandOutput, python_executable, run_command
from .versions import detect_tool_versions

__all__ = [
    "ROOT_MARKERS",
    "CommandOutput",
    "RootMarker",
    "consume",
    "detect_tool_versions",
    "file_lock",
    "python_executable",
    "resolve_project_root",
    "run_command",
]
