"""typewiz – Python Type Checker toolkit.

Provides utilities for collecting typing diagnostics from pyright, mypy, and
custom plugins, aggregating them into manifests and dashboards for progress
tracking.
"""

from __future__ import annotations

from .api import AuditResult, run_audit  # noqa: F401
from .config import AuditConfig, Config, load_config  # noqa: F401
from .dashboard import build_summary, load_manifest, render_markdown  # noqa: F401
from .html_report import render_html  # noqa: F401
from .summary_types import SummaryData  # noqa: F401

__all__ = [
    "__version__",
    "build_summary",
    "load_manifest",
    "render_markdown",
    "render_html",
    "AuditConfig",
    "Config",
    "load_config",
    "run_audit",
    "AuditResult",
    "SummaryData",
]

__version__ = "0.0.1"
