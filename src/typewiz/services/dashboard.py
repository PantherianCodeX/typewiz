# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Dashboard generation and persistence services.

This module provides high-level functions for loading manifest data,
rendering it in various formats (JSON, Markdown, HTML), and persisting
dashboard outputs to the filesystem.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from typewiz.core.model_types import DashboardFormat, DashboardView, LogComponent
from typewiz.dashboard import build_summary, load_manifest, render_markdown
from typewiz.dashboard.render_html import render_html
from typewiz.logging import structured_extra
from typewiz.runtime import normalise_enums_for_json

if TYPE_CHECKING:
    from pathlib import Path

    from typewiz.core.summary_types import SummaryData

logger: logging.Logger = logging.getLogger("typewiz.services.dashboard")


def _ensure_parent(path: Path) -> None:
    """Ensure the parent directory exists for a given path.

    Args:
        path: File path whose parent directory should be created.
    """
    path.parent.mkdir(parents=True, exist_ok=True)


def load_summary_from_manifest(manifest_path: Path) -> SummaryData:
    """Load a manifest file and build a dashboard summary from it.

    Args:
        manifest_path: Filesystem path to the manifest JSON file.

    Returns:
        Structured summary data suitable for dashboard rendering.
    """
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
    """Render a dashboard summary in the specified format.

    Args:
        summary: Pre-built summary data to render.
        format: Output format (JSON, Markdown, or HTML).
        default_view: Default view for HTML rendering (e.g., "files", "folders").

    Returns:
        Rendered dashboard content as a string.
    """
    view = default_view if isinstance(default_view, DashboardView) else DashboardView.from_str(default_view)
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
    """Write dashboard outputs to one or more file paths.

    Args:
        summary: Dashboard summary data to render.
        json_path: Optional path for JSON output.
        markdown_path: Optional path for Markdown output.
        html_path: Optional path for HTML output.
        default_view: Default view for HTML rendering.
    """
    view = default_view if isinstance(default_view, DashboardView) else DashboardView.from_str(default_view)
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
    """Format a payload as indented JSON with trailing newline.

    Args:
        payload: Data structure to serialize.

    Returns:
        JSON-formatted string with 2-space indentation and trailing newline.
    """
    return json.dumps(payload, indent=2) + "\n"


__all__ = [
    "emit_dashboard_outputs",
    "load_summary_from_manifest",
    "render_dashboard_summary",
]
