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

"""Dashboard generation and persistence services.

This module provides high-level functions for loading manifest data,
rendering it in various formats (JSON, Markdown, HTML), and persisting
dashboard outputs to the filesystem.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from ratchetr.core.model_types import DashboardFormat, DashboardView, LogComponent
from ratchetr.dashboard import build_summary, load_manifest, render_markdown
from ratchetr.dashboard.render_html import render_html
from ratchetr.json import JSONValue, normalise_enums_for_json
from ratchetr.logging import structured_extra

if TYPE_CHECKING:
    from pathlib import Path

    from ratchetr.core.summary_types import SummaryData

logger: logging.Logger = logging.getLogger("ratchetr.services.dashboard")


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
    output_format: DashboardFormat,
    default_view: DashboardView | str,
) -> str:
    """Render a dashboard summary in the specified format.

    Args:
        summary: Pre-built summary data to render.
        output_format: Output format (JSON, Markdown, or HTML).
        default_view: Default view for HTML rendering (e.g., "files", "folders").

    Returns:
        Rendered dashboard content as a string.
    """
    view = default_view if isinstance(default_view, DashboardView) else DashboardView.from_str(default_view)
    logger.debug(
        "Rendering dashboard summary (%s)",
        output_format.value,
        extra=structured_extra(component=LogComponent.DASHBOARD, details={"view": view.value}),
    )
    if output_format is DashboardFormat.JSON:
        return _format_json(normalise_enums_for_json(summary))
    if output_format is DashboardFormat.MARKDOWN:
        return render_markdown(summary)
    return render_html(summary, default_view=view.value)


def emit_dashboard_outputs(
    summary: SummaryData,
    *,
    json_path: Path | None,
    markdown_path: Path | None,
    html_path: Path | None,
    default_view: DashboardView | str,
    dry_run: bool = False,
) -> None:
    """Write dashboard outputs to one or more file paths.

    Args:
        summary: Dashboard summary data to render.
        json_path: Optional path for JSON output.
        markdown_path: Optional path for Markdown output.
        html_path: Optional path for HTML output.
        default_view: Default view for HTML rendering.
        dry_run: If True, render but don't write files (for validation).
    """
    view = default_view if isinstance(default_view, DashboardView) else DashboardView.from_str(default_view)
    if json_path:
        payload = normalise_enums_for_json(summary)
        content = _format_json(payload)
        if not dry_run:
            _ensure_parent(json_path)
            _ = json_path.write_text(content, encoding="utf-8")
            logger.info(
                "Wrote dashboard JSON to %s",
                json_path,
                extra=structured_extra(component=LogComponent.DASHBOARD, path=json_path),
            )
        else:
            logger.info(
                "Would write dashboard JSON to %s (dry-run)",
                json_path,
                extra=structured_extra(component=LogComponent.DASHBOARD, path=json_path),
            )
    if markdown_path:
        content = render_markdown(summary)
        if not dry_run:
            _ensure_parent(markdown_path)
            _ = markdown_path.write_text(content, encoding="utf-8")
            logger.info(
                "Wrote dashboard markdown to %s",
                markdown_path,
                extra=structured_extra(component=LogComponent.DASHBOARD, path=markdown_path),
            )
        else:
            logger.info(
                "Would write dashboard markdown to %s (dry-run)",
                markdown_path,
                extra=structured_extra(component=LogComponent.DASHBOARD, path=markdown_path),
            )
    if html_path:
        content = render_html(summary, default_view=view.value)
        if not dry_run:
            _ensure_parent(html_path)
            _ = html_path.write_text(content, encoding="utf-8")
            logger.info(
                "Wrote dashboard html to %s",
                html_path,
                extra=structured_extra(component=LogComponent.DASHBOARD, path=html_path),
            )
        else:
            logger.info(
                "Would write dashboard html to %s (dry-run)",
                html_path,
                extra=structured_extra(component=LogComponent.DASHBOARD, path=html_path),
            )


def _format_json(payload: JSONValue) -> str:
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
