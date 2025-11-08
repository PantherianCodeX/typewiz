# Copyright (c) 2024 PantherianCodeX

"""Public API façade for audit orchestration."""

from __future__ import annotations

from typewiz.audit.api import AuditResult, run_audit

__all__ = ["AuditResult", "run_audit"]
