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

"""Static HTML dashboard generation for s11r2 progress.

The HTML dashboard is generated from the same sources as the Markdown progress
board and is intended to provide an at-a-glance monitoring view.

No manual roll-ups are permitted: the dashboard must be fully derived from the
canonical registries under `docs/_internal/policy/s11r2/registers/`.

This renderer intentionally supports only a small Markdown subset that matches
our generated outputs (headings, lists, fenced code blocks, inline code, and
GFM tables). It is dependency-free.
"""

from __future__ import annotations

import datetime as dt
import html
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scripts.docs.s11r2_progress.legend import StatusLegend
    from scripts.docs.s11r2_progress.metrics import Metrics
    from scripts.docs.s11r2_progress.models import IssueReport


@dataclass(frozen=True, slots=True)
class DashboardLinks:
    registry_index_href: str
    progress_board_href: str
    status_legend_href: str


_TABLE_ROW_RE = re.compile(r"^\|.*\|\s*$")
_TABLE_SEP_RE = re.compile(r"^\|\s*:?[-]{3,}:?\s*(\|\s*:?[-]{3,}:?\s*)+\|\s*$")
_FENCE_RE = re.compile(r"^```")
_MIN_TABLE_LINES = 2


def _anchor_id(title: str) -> str:
    """Convert a title into a stable anchor id.

    Args:
        title: Section title text.

    Returns:
        URL-safe anchor id.
    """
    slug = re.sub(r"[^a-zA-Z0-9\s-]", "", title).strip().lower()
    slug = re.sub(r"\s+", "-", slug)
    return slug or "section"


def _render_inline(text: str) -> str:
    """Render a small inline subset.

    We support inline code, emphasis, and plain text. This intentionally does
    *not* attempt full Markdown semantics.

    Args:
        text: Inline markdown text.

    Returns:
        HTML-safe inline string.
    """
    parts = text.split("`")
    out: list[str] = []
    for idx, part in enumerate(parts):
        if idx % 2 == 1:
            out.append(f"<code>{html.escape(part)}</code>")
            continue
        escaped = html.escape(part)
        escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)
        out.append(escaped)
    return "".join(out)


def _parse_md_table(lines: list[str]) -> str:
    """Parse a best-effort GFM table and render as HTML.

    If the captured block is not a valid table, the caller should render it as
    paragraphs.

    Args:
        lines: Markdown table lines.

    Returns:
        HTML table string.

    Raises:
        ValueError: If the input does not look like a GFM table.
    """
    if len(lines) < _MIN_TABLE_LINES or not _TABLE_SEP_RE.match(lines[1]):
        msg = "Not a valid GFM table"
        raise ValueError(msg)

    header_cells = [c.strip() for c in lines[0].strip("|").split("|")]
    body_rows = [[c.strip() for c in row.strip("|").split("|")] for row in lines[2:] if row.strip()]

    # Normalize body row length to header length.
    norm_rows: list[list[str]] = []
    for row in body_rows:
        normalized = row
        if len(normalized) < len(header_cells):
            normalized = [*normalized, *([""] * (len(header_cells) - len(normalized)))]
        elif len(normalized) > len(header_cells):
            normalized = normalized[: len(header_cells)]
        norm_rows.append(normalized)

    out: list[str] = []
    out.extend([
        "<table>",
        "<thead><tr>" + "".join(f"<th>{_render_inline(c)}</th>" for c in header_cells) + "</tr></thead>",
        "<tbody>",
    ])
    out.extend("<tr>" + "".join(f"<td>{_render_inline(c)}</td>" for c in row) + "</tr>" for row in norm_rows)
    out.append("</tbody></table>")
    return "\n".join(out)


@dataclass
class _RenderState:
    out: list[str]
    in_code: bool
    code_lines: list[str]
    in_table: bool
    table_lines: list[str]
    in_list: bool
    list_items: list[str]


def _flush_code(state: _RenderState) -> None:
    if not state.in_code:
        return
    state.out.extend([
        "<pre><code>",
        html.escape("\n".join(state.code_lines)),
        "</code></pre>",
    ])
    state.in_code = False
    state.code_lines = []


def _flush_table(state: _RenderState) -> None:
    if not state.in_table:
        return

    try:
        state.out.append(_parse_md_table(state.table_lines))
    except ValueError:
        state.out.extend(f"<p>{_render_inline(line_text)}</p>" for line_text in state.table_lines if line_text.strip())

    state.in_table = False
    state.table_lines = []


def _flush_list(state: _RenderState) -> None:
    if not state.in_list:
        return
    state.out.append("<ul>")
    state.out.extend(f"<li>{_render_inline(item)}</li>" for item in state.list_items)
    state.out.append("</ul>")
    state.in_list = False
    state.list_items = []


def _start_code_block(state: _RenderState) -> None:
    _flush_list(state)
    _flush_table(state)
    state.in_code = True


def _handle_fence(line: str, state: _RenderState) -> bool:
    if not _FENCE_RE.match(line):
        return False
    if state.in_code:
        _flush_code(state)
    else:
        _start_code_block(state)
    return True


def _handle_code_line(line: str, state: _RenderState) -> bool:
    if not state.in_code:
        return False
    state.code_lines.append(line)
    return True


def _handle_table_line(line: str, state: _RenderState) -> bool:
    if _TABLE_ROW_RE.match(line):
        _flush_list(state)
        state.in_table = True
        state.table_lines.append(line)
        return True
    if state.in_table:
        _flush_table(state)
    return False


def _handle_blank(line: str, state: _RenderState) -> bool:
    if line.strip():
        return False
    _flush_list(state)
    state.out.append("")
    return True


def _handle_heading(line: str, state: _RenderState) -> bool:
    prefixes = ("#### ", "### ", "## ", "# ")
    for idx, prefix in enumerate(prefixes, start=1):
        if line.startswith(prefix):
            _flush_list(state)
            level = 5 - idx
            tag = f"h{level}"
            state.out.append(f"<{tag}>{_render_inline(line[len(prefix) :])}</{tag}>")
            return True
    return False


def _handle_list_item(line: str, state: _RenderState) -> bool:
    stripped = line.lstrip()
    if not stripped.startswith("- "):
        return False
    if not state.in_list:
        state.in_list = True
    state.list_items.append(stripped[2:])
    return True


def _handle_paragraph(line: str, state: _RenderState) -> None:
    _flush_list(state)
    state.out.append(f"<p>{_render_inline(line)}</p>")


def _clean_lines(out: list[str]) -> list[str]:
    cleaned: list[str] = []
    for line in out:
        if not line and cleaned and not cleaned[-1]:
            continue
        cleaned.append(line)
    return cleaned


def _render_md_block(md: str) -> str:
    """Render a small Markdown subset into HTML.

    Args:
        md: Markdown text to render.

    Returns:
        HTML string representing the Markdown block.
    """
    state = _RenderState(
        out=[],
        in_code=False,
        code_lines=[],
        in_table=False,
        table_lines=[],
        in_list=False,
        list_items=[],
    )

    for raw in md.splitlines():
        line = raw.rstrip("\n")
        if _handle_fence(line, state):
            continue
        if _handle_code_line(line, state):
            continue
        if _handle_table_line(line, state):
            continue
        if _handle_blank(line, state):
            continue
        if _handle_heading(line, state):
            continue
        if _handle_list_item(line, state):
            continue
        _handle_paragraph(line, state)

    _flush_list(state)
    _flush_code(state)
    _flush_table(state)

    return "\n".join(_clean_lines(state.out))


def _render_issue_list(label: str, items: list[str]) -> str:
    """Render a severity-tagged HTML list for issues.

    Args:
        label: Severity label to render.
        items: Issue messages to render.

    Returns:
        HTML list string.
    """
    if not items:
        return "<p><em>None.</em></p>"
    li = "".join(f'<li><span class="sev {label}">{label}</span> {html.escape(m)}</li>' for m in items)
    return f'<ul class="issues">{li}</ul>'


def _render_validation_card(report: IssueReport) -> str:
    """Render the validation findings HTML card.

    Args:
        report: Aggregated issue report.

    Returns:
        HTML string for the validation card.
    """
    errors = [i.message for i in report.errors]
    warns = [i.message for i in report.warnings]
    infos = [i.message for i in report.infos]

    summary = (
        f"<p>Errors: <strong>{len(errors)}</strong> · Warnings: <strong>{len(warns)}</strong> · "
        f"Info: <strong>{len(infos)}</strong></p>"
    )
    return "\n".join([
        '<div class="card" id="validation">',
        "<h2>Validation findings</h2>",
        summary,
        "<h3>Errors</h3>",
        _render_issue_list("ERROR", errors),
        "<h3>Warnings</h3>",
        _render_issue_list("WARN", warns),
        "<h3>Info</h3>",
        _render_issue_list("INFO", infos),
        "</div>",
    ])


def _render_legend_card(legend: StatusLegend) -> str:
    """Render the status legend HTML card.

    Args:
        legend: Status legend to render.

    Returns:
        HTML string for the legend card.
    """
    row_lines: list[str] = []
    for code in legend.codes:
        label = html.escape(legend.label_for(code))
        meaning = html.escape(legend.meaning_for(code))
        row_lines.append(f"<tr><td><code>{html.escape(code)}</code></td><td>{label}</td><td>{meaning}</td></tr>")
    rows = "\n".join(row_lines)
    return "\n".join([
        '<div class="card" id="status-legend">',
        "<h2>Status legend</h2>",
        "<table>",
        "<thead><tr><th>Code</th><th>Label</th><th>Meaning</th></tr></thead>",
        f"<tbody>{rows}</tbody>",
        "</table>",
        "</div>",
    ])


def render_dashboard(
    *,
    legend: StatusLegend,
    metrics: Metrics,
    report: IssueReport,
    links: DashboardLinks,
    now: dt.datetime | None = None,
) -> str:
    """Render the full HTML dashboard.

    Args:
        legend: Status legend to render.
        metrics: Computed metrics payload.
        report: Aggregated issue report.
        links: Related artifact links.
        now: Optional timestamp override.

    Returns:
        HTML document as a string.
    """
    now_utc = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)

    toc_items: list[str] = [
        '<li><a href="#validation">Validation findings</a></li>',
        '<li><a href="#status-legend">Status legend</a></li>',
    ]

    metric_cards: list[str] = []
    for block in metrics.blocks:
        aid = _anchor_id(block.title)
        toc_items.append(f'<li><a href="#{aid}">{html.escape(block.title)}</a></li>')
        metric_cards.append(
            "\n".join([
                f'<div class="card" id="{aid}">',
                f"<h2>{html.escape(block.title)}</h2>",
                f'<div class="mdblock">{_render_md_block(block.body_md)}</div>',
                "</div>",
            ])
        )

    nav_links = (
        '<ul class="nav">'
        f'<li><a href="{html.escape(links.registry_index_href)}">Registry index</a></li>'
        f'<li><a href="{html.escape(links.progress_board_href)}">Progress board (Markdown)</a></li>'
        f'<li><a href="{html.escape(links.status_legend_href)}">Status legend</a></li>'
        "</ul>"
    )

    toc = '<ul class="toc">' + "".join(toc_items) + "</ul>"

    return "\n".join([
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        "<title>s11r2 progress dashboard</title>",
        "<style>",
        (
            "body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,"
            "Cantarell,Noto Sans,sans-serif;margin:0;background:#0b0d10;color:#e7e7e7;}"
        ),
        "a{color:#9dd0ff;text-decoration:none}a:hover{text-decoration:underline}",
        "header{padding:18px 22px;border-bottom:1px solid #1b2330;background:#0f131a}",
        "header h1{margin:0;font-size:18px}",
        ".sub{margin:6px 0 0 0;color:#b6c2d1;font-size:13px}",
        "main{padding:18px 22px}",
        ".layout{max-width:1200px;margin:0 auto;display:grid;grid-template-columns:260px 1fr;gap:16px}",
        ".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:14px}",
        ".sidebar-card{position:sticky;top:16px;align-self:start}",
        (
            ".card{background:#101723;border:1px solid #1b2330;border-radius:12px;"
            "padding:14px 14px 10px 14px;box-shadow:0 2px 12px rgba(0,0,0,.25)}"
        ),
        ".sidebar-card h2{margin:0 0 8px 0;font-size:16px}",
        ".sidebar-card h3{margin:12px 0 6px 0;font-size:13px}",
        ".card h2{margin:0 0 10px 0;font-size:16px}",
        ".card h3{margin:12px 0 8px 0;font-size:14px}",
        ".nav{margin:10px 0 0 0;padding-left:18px;font-size:13px;color:#b6c2d1}",
        ".toc{margin:10px 0 0 0;padding-left:18px;font-size:13px;color:#b6c2d1}",
        ".mdblock table{border-collapse:collapse;width:100%;margin:10px 0}",
        ".mdblock th,.mdblock td{border:1px solid #1b2330;padding:6px 8px;vertical-align:top;font-size:13px}",
        ".mdblock th{background:#0f131a}",
        ".mdblock pre{background:#0f131a;border:1px solid #1b2330;border-radius:10px;padding:10px;overflow:auto}",
        ".mdblock code{background:#0f131a;border:1px solid #1b2330;border-radius:6px;padding:1px 5px}",
        ".issues{padding-left:18px;font-size:13px}",
        (
            ".sev{display:inline-block;font-size:11px;letter-spacing:.02em;"
            "padding:2px 6px;border-radius:999px;margin-right:6px;border:1px solid #1b2330;background:#0f131a}"
        ),
        ".sev.ERROR{border-color:#ff4d4f;color:#ffb3b3}",
        ".sev.WARN{border-color:#fadb14;color:#fff5a3}",
        ".sev.INFO{border-color:#40a9ff;color:#bfe3ff}",
        "@media (max-width: 980px){.layout{grid-template-columns:1fr}.sidebar-card{position:static}}",
        "</style>",
        "</head>",
        "<body>",
        "<header>",
        "<h1>s11r2 progress dashboard</h1>",
        f'<p class="sub">Generated: {html.escape(now_utc.isoformat(timespec="seconds"))}</p>',
        "</header>",
        "<main>",
        '<div class="layout">',
        '<aside class="card sidebar-card">',
        "<h2>Index</h2>",
        "<h3>Links</h3>",
        nav_links,
        "<h3>Sections</h3>",
        toc,
        "</aside>",
        "<section>",
        '<div class="grid">',
        _render_validation_card(report),
        _render_legend_card(legend),
        *metric_cards,
        "</div>",
        "</section>",
        "</div>",
        "</main>",
        "</body>",
        "</html>",
    ])


__all__ = [
    "DashboardLinks",
    "render_dashboard",
]
