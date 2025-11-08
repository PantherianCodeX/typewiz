"""Audit service façade used by CLI layers."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from typewiz.audit.api import AuditResult
from typewiz.audit.api import run_audit as _run_audit
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
    """Run the configured audit and return structured results."""

    return _run_audit(
        project_root=project_root,
        config=config,
        override=override,
        full_paths=full_paths,
        persist_outputs=persist_outputs,
        build_summary_output=build_summary_output,
        write_manifest_to=write_manifest_to,
    )
