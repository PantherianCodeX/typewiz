# Copyright 2025 CrownOps Engineering
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Audit service façade used by CLI layers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ratchetr.audit.api import AuditResult
from ratchetr.audit.api import run_audit as _run_audit

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from ratchetr.config import AuditConfig, Config

__all__ = ["AuditResult", "run_audit"]


def run_audit(
    *,
    project_root: Path,
    config: Config | None = None,
    override: AuditConfig | None = None,
    include_paths: Sequence[str] | None = None,
    build_summary_output: bool = False,
) -> AuditResult:
    """Run the configured audit and return structured results.

    Does NOT write any files (manifest or dashboard). Returns data structures
    that can be persisted by the service layer.

    Args:
        project_root: Repository root location. Must be provided; root discovery
            happens at the CLI layer via resolve_paths().
        config: Loaded `Config` object overriding file discovery.
        override: Additional overrides applied on top of ``config``.
        include_paths: Explicit include list overriding config values.
        build_summary_output: Whether to produce dashboard payloads.

    Returns:
        `AuditResult` returned by the lower-level audit orchestrator.
    """
    return _run_audit(
        project_root=project_root,
        config=config,
        override=override,
        include_paths=include_paths,
        build_summary_output=build_summary_output,
    )
