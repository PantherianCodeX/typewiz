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

"""Rendering for generated s11r2 progress outputs.

Outputs:
- `docs/_internal/policy/s11r2/progress/progress_board.md` (Markdown)

The progress board is intended to be a readable monitoring artifact.
It is fully generated from the canonical registries under
`docs/_internal/policy/s11r2/registers/` and MUST NOT require any manual roll-ups.
"""

from __future__ import annotations

import datetime as dt
import os
from pathlib import Path
from typing import TYPE_CHECKING

from scripts.docs.s11r2_progress.generated_blocks import BEGIN_MARKER, END_MARKER
from scripts.docs.s11r2_progress.md import render_labeled_bullets, render_md_table

if TYPE_CHECKING:
    from scripts.docs.s11r2_progress.legend import StatusLegend
    from scripts.docs.s11r2_progress.metrics import Metrics
    from scripts.docs.s11r2_progress.models import IssueReport
    from scripts.docs.s11r2_progress.paths import S11R2Paths


def _rel_href(*, start_dir: Path, target: Path) -> str:
    """Return a portable relative href from start_dir to target."""
    rel = os.path.relpath(target.resolve().as_posix(), start_dir.resolve().as_posix())
    return Path(rel).as_posix()


def _render_legend_table(*, legend: StatusLegend) -> str:
    header = ("Code", "Label", "Meaning")
    rows = [(code, legend.label_for(code), legend.meaning_for(code)) for code in legend.codes]
    return render_md_table(header, rows)


def _render_issue_sections(*, report: IssueReport) -> str:
    lines: list[str] = []

    errors = report.errors
    warns = report.warnings
    infos = report.infos

    lines.extend([
        f"- Errors: {len(errors)}",
        f"- Warnings: {len(warns)}",
        f"- Info: {len(infos)}",
    ])

    if not (errors or warns or infos):
        return "\n".join(lines)

    if errors:
        lines.extend([
            "",
            "#### Errors",
            "",
            render_labeled_bullets((i.message for i in errors), label="ERROR"),
        ])

    if warns:
        lines.extend([
            "",
            "#### Warnings",
            "",
            render_labeled_bullets((i.message for i in warns), label="WARN"),
        ])

    if infos:
        lines.extend([
            "",
            "#### Info",
            "",
            render_labeled_bullets((i.message for i in infos), label="INFO"),
        ])

    return "\n".join(lines)


def render_generated_block_body(*, metrics: Metrics, report: IssueReport, legend: StatusLegend) -> str:
    """Render the body for the generated monitoring block (no markers).

    Args:
        metrics: Computed metrics payload.
        report: Aggregated issue report.
        legend: Status legend for rendering.

    Returns:
        Markdown block body for the progress board.
    """
    lines: list[str] = []

    lines.extend([
        "## Generated monitoring",
        "",
        "### Validation findings",
        "",
        _render_issue_sections(report=report),
        "",
        "### Status legend",
        "",
        _render_legend_table(legend=legend),
        "",
        "### Derived metrics",
        "",
    ])

    for block in metrics.blocks:
        lines.extend((f"#### {block.title}", ""))
        lines.extend(block.body_md.rstrip().splitlines())
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def compose_progress_board_output(
    *,
    paths: S11R2Paths,
    metrics: Metrics,
    report: IssueReport,
    legend: StatusLegend,
    now: dt.datetime | None = None,
) -> str:
    """Compose the full generated progress board markdown.

    Args:
        paths: Resolved s11r2 paths.
        metrics: Computed metrics payload.
        report: Aggregated issue report.
        legend: Status legend for rendering.
        now: Optional timestamp for rendering.

    Returns:
        Full progress board markdown content.
    """
    now_utc = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)

    out_file = paths.generated_progress_board
    out_dir = out_file.parent

    registry_index_href = _rel_href(start_dir=out_dir, target=paths.registry_index)
    status_legend_href = _rel_href(start_dir=out_dir, target=paths.status_legend)
    dashboard_href = _rel_href(start_dir=out_dir, target=paths.generated_dashboard)

    generated_body = render_generated_block_body(metrics=metrics, report=report, legend=legend)

    lines: list[str] = []

    lines.extend([
        "# s11r2 progress board",
        "",
        "## Generated",
        "",
        f"Timestamp: {now_utc.isoformat(timespec='seconds')}",
        "",
        (
            "This file is generated from the canonical s11r2 registries. "
            "Edit source registries under `../registers/`, then regenerate progress outputs."
        ),
        "",
        "## Links",
        "",
        f"- Registry index: [{registry_index_href}]({registry_index_href})",
        f"- Status legend: [{status_legend_href}]({status_legend_href})",
        f"- Dashboard: [{dashboard_href}]({dashboard_href})",
        "",
        "## Regeneration",
        "",
        "Run from repo root:",
        "",
        "- `python scripts/docs/s11r2-progress.py --write`",
        "- `python scripts/docs/s11r2-progress.py --write --write-html`",
        "",
        BEGIN_MARKER,
        "",
        generated_body.rstrip(),
        END_MARKER,
        "",
    ])

    return "\n".join(lines).rstrip() + "\n"


__all__ = [
    "compose_progress_board_output",
    "render_generated_block_body",
]
