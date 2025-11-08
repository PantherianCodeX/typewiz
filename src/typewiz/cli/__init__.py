# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""CLI package for typewiz."""

from __future__ import annotations

from .app import main, write_config_template
from .helpers.formatting import (
    SUMMARY_FIELD_CHOICES,
    print_readiness_summary,
    print_summary,
    query_readiness,
)

try:  # pragma: no cover - defensive import guard
    from .. import __version__ as _pkg_version
except Exception:  # pragma: no cover - fallback for partial initialisation
    _pkg_version = "0.0.0"

__version__ = _pkg_version

__all__ = [
    "__version__",
    "SUMMARY_FIELD_CHOICES",
    "main",
    "print_readiness_summary",
    "print_summary",
    "query_readiness",
    "write_config_template",
]
