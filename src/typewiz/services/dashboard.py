# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from typewiz.core.model_types import DashboardFormat, DashboardView, LogComponent
from typewiz.core.summary_types import SummaryData
from typewiz.dashboard import build_summary, load_manifest, render_markdown
from typewiz.dashboard.render_html import render_html
from typewiz.logging import structured_extra
from typewiz.runtime import normalise_enums_for_json

logger: logging.Logger = logging.getLogger("typewiz.services.dashboard")


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_summary_from_manifest(manifest_path: Path) -> SummaryData:
    manifest = load_manifest(manifest_path)
    summary = build_summary(manifest)
    logger.info(
        "Loaded dashboard summary from %s",
        manifest_path,
        extra=structured_extra(component=LogComponent.DASHBOARD, manifest=manifest_path),
    )
    return summary


def render_dashboard_summary(
    summary: SummaryData,
    *,
    format: DashboardFormat,
    default_view: DashboardView | str,
) -> str:
    view = (
        default_view
        if isinstance(default_view, DashboardView)
        else DashboardView.from_str(default_view)
    )
    logger.debug(
        "Rendering dashboard summary (%s)",
        format.value,
        extra=structured_extra(component=LogComponent.DASHBOARD, details={"view": view.value}),
    )
    if format is DashboardFormat.JSON:
        return _format_json(normalise_enums_for_json(summary))
    if format is DashboardFormat.MARKDOWN:
        return render_markdown(summary)
    return render_html(summary, default_view=view.value)


def emit_dashboard_outputs(
    summary: SummaryData,
    *,
    json_path: Path | None,
    markdown_path: Path | None,
    html_path: Path | None,
    default_view: DashboardView | str,
) -> None:
    view = (
        default_view
        if isinstance(default_view, DashboardView)
        else DashboardView.from_str(default_view)
    )
    if json_path:
        _ensure_parent(json_path)
        payload = normalise_enums_for_json(summary)
        _ = json_path.write_text(_format_json(payload), encoding="utf-8")
        logger.info(
            "Wrote dashboard JSON to %s",
            json_path,
            extra=structured_extra(component=LogComponent.DASHBOARD, path=json_path),
        )
    if markdown_path:
        _ensure_parent(markdown_path)
        _ = markdown_path.write_text(render_markdown(summary), encoding="utf-8")
        logger.info(
            "Wrote dashboard markdown to %s",
            markdown_path,
            extra=structured_extra(component=LogComponent.DASHBOARD, path=markdown_path),
        )
    if html_path:
        _ensure_parent(html_path)
        _ = html_path.write_text(render_html(summary, default_view=view.value), encoding="utf-8")
        logger.info(
            "Wrote dashboard html to %s",
            html_path,
            extra=structured_extra(component=LogComponent.DASHBOARD, path=html_path),
        )


def _format_json(payload: Any) -> str:
    import json

    return json.dumps(payload, indent=2) + "\n"


__all__ = [
    "emit_dashboard_outputs",
    "load_summary_from_manifest",
    "render_dashboard_summary",
]
