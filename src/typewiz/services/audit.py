# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Audit service façade used by CLI layers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from typewiz.audit.api import AuditResult
from typewiz.audit.api import run_audit as _run_audit

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from typewiz.config import AuditConfig, Config

__all__ = ["AuditResult", "run_audit"]


def run_audit(
    *,
    project_root: Path | None = None,
    config: Config | None = None,
    override: AuditConfig | None = None,
    full_paths: Sequence[str] | None = None,
    persist_outputs: bool = True,
    build_summary_output: bool = False,
    write_manifest_to: Path | None = None,
) -> AuditResult:
    """Run the configured audit and return structured results.

    Args:
        project_root: Repository root location.
        config: Loaded ``Config`` object overriding file discovery.
        override: Additional overrides applied on top of ``config``.
        full_paths: Explicit include list overriding config values.
        persist_outputs: Whether to write manifest outputs.
        build_summary_output: Whether to produce dashboard payloads.
        write_manifest_to: Optional path override for manifest output.

    Returns:
        ``AuditResult`` returned by the lower-level audit orchestrator.
    """
    return _run_audit(
        project_root=project_root,
        config=config,
        override=override,
        full_paths=full_paths,
        persist_outputs=persist_outputs,
        build_summary_output=build_summary_output,
        write_manifest_to=write_manifest_to,
    )
