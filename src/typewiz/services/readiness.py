# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

from __future__ import annotations

from collections.abc import Sequence
from typing import cast

from typewiz.core.model_types import ReadinessLevel, ReadinessStatus, SeverityLevel
from typewiz.core.summary_types import SummaryData
from typewiz.readiness.views import (
    FileReadinessPayload,
    FolderReadinessPayload,
    ReadinessValidationError,
    ReadinessViewResult,
)
from typewiz.readiness.views import (
    collect_readiness_view as _collect_readiness_view,
)


def collect_readiness_view(
    summary: SummaryData,
    *,
    level: ReadinessLevel,
    statuses: Sequence[ReadinessStatus] | None,
    limit: int,
    severities: Sequence[SeverityLevel] | None = None,
) -> ReadinessViewResult:
    return _collect_readiness_view(
        summary,
        level=level,
        statuses=statuses,
        limit=limit,
        severities=severities,
    )


def format_readiness_summary(  # noqa: PLR0913
    summary: SummaryData,
    *,
    level: ReadinessLevel,
    statuses: Sequence[ReadinessStatus] | None,
    limit: int,
    severities: Sequence[SeverityLevel] | None = None,
    detailed: bool = False,
) -> list[str]:
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
            dict[ReadinessStatus, list[FolderReadinessPayload]],
            view,
        )
        for status, folder_entries in folder_view.items():
            lines.append(f"[typewiz] readiness {level.value} status={status.value} (top {limit})")
            if not folder_entries:
                lines.append("  <none>")
                continue
            for folder_entry in folder_entries:
                label = f"  {folder_entry['path']}: {folder_entry['count']}"
                lines.append(_format_counts(label, folder_entry))
        return lines

    file_view: dict[ReadinessStatus, list[FileReadinessPayload]] = cast(
        dict[ReadinessStatus, list[FileReadinessPayload]],
        view,
    )
    for status, file_entries in file_view.items():
        lines.append(f"[typewiz] readiness {level.value} status={status.value} (top {limit})")
        if not file_entries:
            lines.append("  <none>")
            continue
        for file_entry in file_entries:
            label = f"  {file_entry['path']}: {file_entry['diagnostics']}"
            lines.append(_format_counts(label, file_entry))
    return lines


__all__ = [
    "collect_readiness_view",
    "format_readiness_summary",
    "ReadinessValidationError",
]
