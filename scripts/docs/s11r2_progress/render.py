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

from scripts.docs.s11r2_progress.generated_blocks import BEGIN_MARKER, END_MARKER
from scripts.docs.s11r2_progress.legend import StatusLegend
from scripts.docs.s11r2_progress.md import render_labeled_bullets, render_md_table
from scripts.docs.s11r2_progress.metrics import Metrics
from scripts.docs.s11r2_progress.models import IssueReport
from scripts.docs.s11r2_progress.paths import S11R2Paths


def _rel_href(*, start_dir: Path, target: Path) -> str:
    """Return a portable relative href from start_dir to target."""

    rel = os.path.relpath(target.resolve().as_posix(), start_dir.resolve().as_posix())
    return Path(rel).as_posix()


def _render_legend_table(*, legend: StatusLegend) -> str:
    header = ("Code", "Label", "Meaning")
    rows = []
    for code in legend.codes:
        rows.append((code, legend.label_for(code), legend.meaning_for(code)))
    return render_md_table(header, rows)


def _render_issue_sections(*, report: IssueReport) -> str:
    lines: list[str] = []

    errors = report.errors
    warns = report.warnings
    infos = report.infos

    lines.append(f"- Errors: {len(errors)}")
    lines.append(f"- Warnings: {len(warns)}")
    lines.append(f"- Info: {len(infos)}")

    if not (errors or warns or infos):
        return "\n".join(lines)

    if errors:
        lines.append("")
        lines.append("#### Errors")
        lines.append("")
        lines.append(render_labeled_bullets((i.message for i in errors), label="ERROR"))

    if warns:
        lines.append("")
        lines.append("#### Warnings")
        lines.append("")
        lines.append(render_labeled_bullets((i.message for i in warns), label="WARN"))

    if infos:
        lines.append("")
        lines.append("#### Info")
        lines.append("")
        lines.append(render_labeled_bullets((i.message for i in infos), label="INFO"))

    return "\n".join(lines)


def render_generated_block_body(*, metrics: Metrics, report: IssueReport, legend: StatusLegend) -> str:
    """Render the body for the generated monitoring block (no markers)."""

    lines: list[str] = []

    lines.append("## Generated monitoring")
    lines.append("")

    lines.append("### Validation findings")
    lines.append("")
    lines.append(_render_issue_sections(report=report))
    lines.append("")

    lines.append("### Status legend")
    lines.append("")
    lines.append(_render_legend_table(legend=legend))
    lines.append("")

    lines.append("### Derived metrics")
    lines.append("")

    for block in metrics.blocks:
        lines.append(f"#### {block.title}")
        lines.append("")
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
    """Compose the full generated progress board markdown."""

    now_utc = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)

    out_file = paths.generated_progress_board
    out_dir = out_file.parent

    registry_index_href = _rel_href(start_dir=out_dir, target=paths.registry_index)
    status_legend_href = _rel_href(start_dir=out_dir, target=paths.status_legend)
    dashboard_href = _rel_href(start_dir=out_dir, target=paths.generated_dashboard)

    generated_body = render_generated_block_body(metrics=metrics, report=report, legend=legend)

    lines: list[str] = []

    lines.append("# s11r2 progress board")
    lines.append("")
    lines.append(f"_Generated: {now_utc.isoformat(timespec='seconds')}_")
    lines.append("")
    lines.append(
        "This file is generated from the canonical s11r2 registries. "
        "Edit source registries under `../registers/`, then regenerate progress outputs."
    )
    lines.append("")

    lines.append("## Links")
    lines.append("")
    lines.append(f"- Registry index: [{registry_index_href}]({registry_index_href})")
    lines.append(f"- Status legend: [{status_legend_href}]({status_legend_href})")
    lines.append(f"- Dashboard: [{dashboard_href}]({dashboard_href})")
    lines.append("")

    lines.append("## Regeneration")
    lines.append("")
    lines.append("Run from repo root:")
    lines.append("")
    lines.append("- `python scripts/docs/s11r2-progress.py --write`")
    lines.append("- `python scripts/docs/s11r2-progress.py --write --write-html`")
    lines.append("")

    lines.append(BEGIN_MARKER)
    lines.append(generated_body.rstrip())
    lines.append(END_MARKER)
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


__all__ = [
    "compose_progress_board_output",
    "render_generated_block_body",
]
