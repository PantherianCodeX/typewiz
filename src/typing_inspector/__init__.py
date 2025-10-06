"""Typing Inspector package.

Provides utilities for collecting typing diagnostics from pyright and mypy,
aggregating them into a manifest that can be used for progress tracking.
"""

from __future__ import annotations

from .dashboard import build_summary, load_manifest, render_markdown  # noqa: F401
from .html_report import render_html  # noqa: F401
from .config import AuditConfig, Config, load_config  # noqa: F401
from .api import run_audit, AuditResult  # noqa: F401

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
]

__version__ = "0.1.0"
