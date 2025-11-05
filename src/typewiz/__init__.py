"""typewiz - Python Type Checker toolkit.

Provides utilities for collecting typing diagnostics from pyright, mypy, and
custom plugins, aggregating them into manifests and dashboards for progress
tracking.
"""

from __future__ import annotations

from .api import AuditResult, run_audit
from .config import AuditConfig, Config, load_config
from .dashboard import build_summary, load_manifest, render_markdown
from .exceptions import (
    TypewizError,
    TypewizTypeError,
    TypewizValidationError,
)
from .html_report import render_html
from .summary_types import SummaryData
from .typed_manifest import ToolSummary
from .types import Diagnostic, RunResult

__all__ = [
    "AuditConfig",
    "AuditResult",
    "Config",
    "Diagnostic",
    "RunResult",
    "SummaryData",
    "ToolSummary",
    "TypewizError",
    "TypewizTypeError",
    "TypewizValidationError",
    "__version__",
    "build_summary",
    "load_config",
    "load_manifest",
    "render_html",
    "render_markdown",
    "run_audit",
]

__version__ = "0.2.0"
