# Copyright (c) 2024 PantherianCodeX

"""Public API façade for Typewiz orchestration helpers."""

from __future__ import annotations

from typewiz.dashboard import build_summary, load_manifest
from typewiz.dashboard.render_html import render_html
from typewiz.dashboard.render_markdown import render_markdown
from typewiz.services.audit import AuditResult, run_audit
from typewiz.services.dashboard import (
    emit_dashboard_outputs,
    load_summary_from_manifest,
    render_dashboard_summary,
)
from typewiz.services.manifest import (
    ManifestPayloadError,
    ManifestValidationResult,
    manifest_json_schema,
    validate_manifest_file,
)

__all__ = [
    "AuditResult",
    "ManifestPayloadError",
    "ManifestValidationResult",
    "build_summary",
    "emit_dashboard_outputs",
    "load_manifest",
    "load_summary_from_manifest",
    "manifest_json_schema",
    "render_dashboard_summary",
    "render_html",
    "render_markdown",
    "run_audit",
    "validate_manifest_file",
]
