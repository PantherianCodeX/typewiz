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

"""Dashboard module for ratchetr.

This module provides functionality for building, loading, and rendering
ratchetr dashboard summaries. It supports both HTML and Markdown output formats
for visualizing type checking diagnostics and readiness metrics.
"""

from __future__ import annotations

from .build import DashboardTypeError, build_summary, load_manifest
from .render_html import render_html
from .render_markdown import render_markdown

__all__ = [
    "DashboardTypeError",
    "build_summary",
    "load_manifest",
    "render_html",
    "render_markdown",
]
