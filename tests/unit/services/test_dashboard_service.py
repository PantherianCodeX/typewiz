# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Unit tests for dashboard rendering services."""

from __future__ import annotations

from typing import TYPE_CHECKING

from typewiz.core.model_types import DashboardFormat, DashboardView
from typewiz.services import dashboard as dashboard_service

if TYPE_CHECKING:
    from pathlib import Path

    from typewiz.core.summary_types import SummaryData


def test_render_dashboard_summary_formats(sample_summary: SummaryData) -> None:
    json_output = dashboard_service.render_dashboard_summary(
        sample_summary,
        output_format=DashboardFormat.JSON,
        default_view="overview",
    )
    assert json_output.endswith("\n")
    markdown_output = dashboard_service.render_dashboard_summary(
        sample_summary,
        output_format=DashboardFormat.MARKDOWN,
        default_view=DashboardView.OVERVIEW,
    )
    assert "####" in markdown_output
    html_output = dashboard_service.render_dashboard_summary(
        sample_summary,
        output_format=DashboardFormat.HTML,
        default_view="hotspots",
    )
    assert "<!DOCTYPE html>" in html_output or "<html" in html_output


def test_emit_dashboard_outputs_writes_files(tmp_path: Path, sample_summary: SummaryData) -> None:
    json_path = tmp_path / "reports" / "summary.json"
    markdown_path = tmp_path / "reports" / "summary.md"
    html_path = tmp_path / "reports" / "summary.html"
    dashboard_service.emit_dashboard_outputs(
        sample_summary,
        json_path=json_path,
        markdown_path=markdown_path,
        html_path=html_path,
        default_view=DashboardView.OVERVIEW,
    )
    assert json_path.exists()
    assert markdown_path.exists()
    assert html_path.exists()
    assert html_path.read_text(encoding="utf-8").startswith("<")
