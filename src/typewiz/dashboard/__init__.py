# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Dashboard module for typewiz.

This module provides functionality for building, loading, and rendering
typewiz dashboard summaries. It supports both HTML and Markdown output formats
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
