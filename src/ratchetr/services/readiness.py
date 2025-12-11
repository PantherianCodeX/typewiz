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

"""Service façade for readiness computations used by the CLI."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from ratchetr.core.model_types import ReadinessLevel, ReadinessStatus, SeverityLevel
from ratchetr.readiness.views import (
    FileReadinessPayload,
    FolderReadinessPayload,
    ReadinessValidationError,
    ReadinessViewResult,
)
from ratchetr.readiness.views import (
    collect_readiness_view as _collect_readiness_view,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ratchetr.core.summary_types import SummaryData


def collect_readiness_view(
    summary: SummaryData,
    *,
    level: ReadinessLevel,
    statuses: Sequence[ReadinessStatus] | None,
    limit: int,
    severities: Sequence[SeverityLevel] | None = None,
) -> ReadinessViewResult:
    """Collect readiness data from a summary payload with typed validation.

    Args:
        summary: Manifest summary payload.
        level: Readiness granularity (files or folders).
        statuses: Optional subset of statuses to include.
        limit: Max entries per status (`0`= unlimited).
        severities: Optional severity filters.

    Returns:
        Readiness view result structured per ``ReadinessLevel``.

    Note:
        Validation errors raised by `_collect_readiness_view`propagate to the
        caller as ``ReadinessValidationError``.
    """
    return _collect_readiness_view(
        summary,
        level=level,
        statuses=statuses,
        limit=limit,
        severities=severities,
    )


def format_readiness_summary(
    summary: SummaryData,
    *,
    level: ReadinessLevel,
    statuses: Sequence[ReadinessStatus] | None,
    limit: int,
    severities: Sequence[SeverityLevel] | None = None,
    detailed: bool = False,
) -> list[str]:
    """Render a text summary mirroring the legacy CLI readiness report.

    Args:
        summary: Manifest summary payload.
        level: Readiness granularity to render.
        statuses: Optional subset of statuses to include.
        limit: Maximum items per bucket.
        severities: Optional severity filters.
        detailed: Whether to append severity counts to each line.

    Returns:
        List of CLI-friendly lines ready to print.
    """
    view = collect_readiness_view(
        summary,
        level=level,
        statuses=statuses,
        limit=limit,
        severities=severities,
    )
    lines: list[str] = []

    def _format_counts(
        label: str,
        entry: FolderReadinessPayload | FileReadinessPayload,
    ) -> str:
        if not detailed:
            return label
        errors = entry.get("errors", 0)
        warnings = entry.get("warnings", 0)
        information = entry.get("information", 0)
        return f"{label} (errors={errors} warnings={warnings} info={information})"

    if level is ReadinessLevel.FOLDER:
        folder_view: dict[ReadinessStatus, list[FolderReadinessPayload]] = cast(
            "dict[ReadinessStatus, list[FolderReadinessPayload]]",
            view,
        )
        for status, folder_entries in folder_view.items():
            lines.append(f"[ratchetr] readiness {level.value} status={status.value} (top {limit})")
            if not folder_entries:
                lines.append("  <none>")
                continue
            for folder_entry in folder_entries:
                label = f"  {folder_entry['path']}: {folder_entry['count']}"
                lines.append(_format_counts(label, folder_entry))
        return lines

    file_view: dict[ReadinessStatus, list[FileReadinessPayload]] = cast(
        "dict[ReadinessStatus, list[FileReadinessPayload]]",
        view,
    )
    for status, file_entries in file_view.items():
        lines.append(f"[ratchetr] readiness {level.value} status={status.value} (top {limit})")
        if not file_entries:
            lines.append("  <none>")
            continue
        for file_entry in file_entries:
            label = f"  {file_entry['path']}: {file_entry['diagnostics']}"
            lines.append(_format_counts(label, file_entry))
    return lines


__all__ = [
    "ReadinessValidationError",
    "collect_readiness_view",
    "format_readiness_summary",
]
