# Copyright (c) 2024 PantherianCodeX

"""typewiz - Python Type Checker toolkit.

Provides utilities for collecting typing diagnostics from pyright, mypy, and
custom plugins, aggregating them into manifests and dashboards for progress
tracking.
"""

from __future__ import annotations

from typewiz._internal.exceptions import (
    TypewizError,
    TypewizTypeError,
    TypewizValidationError,
)
from typewiz._internal.license import (
    LICENSE_KEY_ENV,
    has_commercial_license,
    license_mode,
)

from .api import AuditResult, run_audit
from .config import AuditConfig, Config, load_config
from .core.summary_types import SummaryData
from .core.types import Diagnostic, RunResult
from .dashboard import build_summary, load_manifest, render_markdown
from .html_report import render_html
from .manifest.typed import ToolSummary
from .ratchet import (
    apply_auto_update as ratchet_apply_auto_update,
)
from .ratchet import (
    build_ratchet_from_manifest as ratchet_build,
)
from .ratchet import (
    compare_manifest_to_ratchet as ratchet_compare,
)
from .ratchet import (
    refresh_signatures as ratchet_refresh,
)

__all__ = [
    "__version__",
    "AuditConfig",
    "AuditResult",
    "Config",
    "Diagnostic",
    "LICENSE_KEY_ENV",
    "RunResult",
    "SummaryData",
    "ToolSummary",
    "TypewizError",
    "TypewizTypeError",
    "TypewizValidationError",
    "build_summary",
    "has_commercial_license",
    "license_mode",
    "load_config",
    "load_manifest",
    "ratchet_apply_auto_update",
    "ratchet_build",
    "ratchet_compare",
    "ratchet_refresh",
    "render_html",
    "render_markdown",
    "run_audit",
]

__version__ = "0.1.0"
