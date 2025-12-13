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

"""Unit tests for dashboard rendering services."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ratchetr.core.model_types import DashboardFormat, DashboardView
from ratchetr.services import dashboard as dashboard_service

if TYPE_CHECKING:
    from pathlib import Path

    from ratchetr.core.summary_types import SummaryData


pytestmark = pytest.mark.unit


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
    assert "### `pyright:current`" in markdown_output
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
