from __future__ import annotations

from typewiz.dashboard import render_markdown
from typewiz.html_report import render_html


def test_render_markdown_snapshot(sample_summary, snapshot_text):
    output = render_markdown(sample_summary)
    assert output == snapshot_text("dashboard.md")


def test_render_html_snapshot(sample_summary, snapshot_text):
    output = render_html(sample_summary)
    assert output == snapshot_text("dashboard.html")
