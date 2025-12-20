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

from dataclasses import dataclass
import datetime as dt
import html
import re

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


def _anchor_id(title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9\s-]", "", title).strip().lower()
    slug = re.sub(r"\s+", "-", slug)
    return slug or "section"


def _render_inline(text: str) -> str:
    """Render a small inline subset.

    We support inline code and plain text. This intentionally does *not* attempt
    full Markdown semantics.
    """

    # Preserve inline code blocks.
    def repl(m: re.Match[str]) -> str:
        return f"<code>{html.escape(m.group(1))}</code>"

    return re.sub(r"`([^`]+)`", repl, html.escape(text))


def _parse_md_table(lines: list[str]) -> str:
    """Parse a best-effort GFM table and render as HTML.

    If the captured block is not a valid table, the caller should render it as
    paragraphs.
    """

    if len(lines) < 2 or not _TABLE_SEP_RE.match(lines[1]):
        raise ValueError("Not a valid GFM table")

    header_cells = [c.strip() for c in lines[0].strip("|").split("|")]
    body_rows = [
        [c.strip() for c in row.strip("|").split("|")]
        for row in lines[2:]
        if row.strip()
    ]

    # Normalize body row length to header length.
    norm_rows: list[list[str]] = []
    for r in body_rows:
        if len(r) < len(header_cells):
            r = [*r, *([""] * (len(header_cells) - len(r)))]
        elif len(r) > len(header_cells):
            r = r[: len(header_cells)]
        norm_rows.append(r)

    out: list[str] = []
    out.append("<table>")
    out.append(
        "<thead><tr>" + "".join(f"<th>{_render_inline(c)}</th>" for c in header_cells) + "</tr></thead>"
    )
    out.append("<tbody>")
    for r in norm_rows:
        out.append("<tr>" + "".join(f"<td>{_render_inline(c)}</td>" for c in r) + "</tr>")
    out.append("</tbody></table>")
    return "\n".join(out)


def _render_md_block(md: str) -> str:
    """Render a small Markdown subset into HTML."""

    lines = md.splitlines()
    out: list[str] = []

    in_code = False
    code_lines: list[str] = []

    in_table = False
    table_lines: list[str] = []

    in_list = False
    list_items: list[str] = []

    def flush_code() -> None:
        nonlocal in_code, code_lines
        if not in_code:
            return
        out.append("<pre><code>")
        out.append(html.escape("\n".join(code_lines)))
        out.append("</code></pre>")
        in_code = False
        code_lines = []

    def flush_table() -> None:
        nonlocal in_table, table_lines
        if not in_table:
            return

        try:
            out.append(_parse_md_table(table_lines))
        except ValueError:
            # Not a valid table; fall back to paragraphs.
            for l in table_lines:
                if l.strip():
                    out.append(f"<p>{_render_inline(l)}</p>")

        in_table = False
        table_lines = []

    def flush_list() -> None:
        nonlocal in_list, list_items
        if not in_list:
            return
        out.append("<ul>")
        for item in list_items:
            out.append(f"<li>{_render_inline(item)}</li>")
        out.append("</ul>")
        in_list = False
        list_items = []

    for raw in lines:
        line = raw.rstrip("\n")

        if _FENCE_RE.match(line):
            if in_code:
                flush_code()
            else:
                flush_list()
                flush_table()
                in_code = True
            continue

        if in_code:
            code_lines.append(line)
            continue

        if _TABLE_ROW_RE.match(line):
            flush_list()
            if not in_table:
                in_table = True
            table_lines.append(line)
            continue

        if in_table:
            flush_table()

        stripped = line.strip()
        if not stripped:
            flush_list()
            out.append("")
            continue

        # Headings
        if line.startswith("#### "):
            flush_list()
            out.append(f"<h4>{_render_inline(line[5:])}</h4>")
            continue
        if line.startswith("### "):
            flush_list()
            out.append(f"<h3>{_render_inline(line[4:])}</h3>")
            continue
        if line.startswith("## "):
            flush_list()
            out.append(f"<h2>{_render_inline(line[3:])}</h2>")
            continue
        if line.startswith("# "):
            flush_list()
            out.append(f"<h1>{_render_inline(line[2:])}</h1>")
            continue

        # Lists (no nesting)
        lstripped = line.lstrip()
        if lstripped.startswith("- "):
            if not in_list:
                in_list = True
            list_items.append(lstripped[2:])
            continue

        flush_list()
        out.append(f"<p>{_render_inline(line)}</p>")

    flush_list()
    flush_code()
    flush_table()

    # Remove consecutive empty lines for cleaner output.
    cleaned: list[str] = []
    for l in out:
        if l == "" and cleaned and cleaned[-1] == "":
            continue
        cleaned.append(l)

    return "\n".join(cleaned)


def _render_validation_card(report: IssueReport) -> str:
    def render_list(label: str, items: list[str]) -> str:
        if not items:
            return "<p><em>None.</em></p>"
        li = "".join(f"<li><span class=\"sev {label}\">{label}</span> {html.escape(m)}</li>" for m in items)
        return f"<ul class=\"issues\">{li}</ul>"

    errors = [i.message for i in report.errors]
    warns = [i.message for i in report.warnings]
    infos = [i.message for i in report.infos]

    return "\n".join(
        [
            '<div class="card" id="validation">',
            "<h2>Validation findings</h2>",
            f"<p>Errors: <strong>{len(errors)}</strong> · Warnings: <strong>{len(warns)}</strong> · Info: <strong>{len(infos)}</strong></p>",
            "<h3>Errors</h3>",
            render_list("ERROR", errors),
            "<h3>Warnings</h3>",
            render_list("WARN", warns),
            "<h3>Info</h3>",
            render_list("INFO", infos),
            "</div>",
        ]
    )


def _render_legend_card(legend: StatusLegend) -> str:
    rows = "\n".join(
        f"<tr><td><code>{html.escape(code)}</code></td><td>{html.escape(legend.label_for(code))}</td><td>{html.escape(legend.meaning_for(code))}</td></tr>"
        for code in legend.codes
    )
    return "\n".join(
        [
            '<div class="card" id="status-legend">',
            "<h2>Status legend</h2>",
            "<table>",
            "<thead><tr><th>Code</th><th>Label</th><th>Meaning</th></tr></thead>",
            f"<tbody>{rows}</tbody>",
            "</table>",
            "</div>",
        ]
    )


def render_dashboard(
    *,
    legend: StatusLegend,
    metrics: Metrics,
    report: IssueReport,
    links: DashboardLinks,
    now: dt.datetime | None = None,
) -> str:
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
            "\n".join(
                [
                    f'<div class="card" id="{aid}">',
                    f"<h2>{html.escape(block.title)}</h2>",
                    f'<div class="mdblock">{_render_md_block(block.body_md)}</div>',
                    "</div>",
                ]
            )
        )

    nav_links = (
        "<ul class=\"nav\">"
        f'<li><a href="{html.escape(links.registry_index_href)}">Registry index</a></li>'
        f'<li><a href="{html.escape(links.progress_board_href)}">Progress board (Markdown)</a></li>'
        f'<li><a href="{html.escape(links.status_legend_href)}">Status legend</a></li>'
        "</ul>"
    )

    toc = "<ul class=\"toc\">" + "".join(toc_items) + "</ul>"

    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            "<title>s11r2 progress dashboard</title>",
            "<style>",
            "body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Cantarell,Noto Sans,sans-serif;margin:0;background:#0b0d10;color:#e7e7e7;}",
            "a{color:#9dd0ff;text-decoration:none}a:hover{text-decoration:underline}",
            "header{padding:18px 22px;border-bottom:1px solid #1b2330;background:#0f131a}",
            "header h1{margin:0;font-size:18px}",
            ".sub{margin:6px 0 0 0;color:#b6c2d1;font-size:13px}",
            "main{padding:18px 22px;max-width:1200px;margin:0 auto}",
            ".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:14px}",
            ".card{background:#101723;border:1px solid #1b2330;border-radius:12px;padding:14px 14px 10px 14px;box-shadow:0 2px 12px rgba(0,0,0,.25)}",
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
            ".sev{display:inline-block;font-size:11px;letter-spacing:.02em;padding:2px 6px;border-radius:999px;margin-right:6px;border:1px solid #1b2330;background:#0f131a}",
            ".sev.ERROR{border-color:#ff4d4f;color:#ffb3b3}",
            ".sev.WARN{border-color:#fadb14;color:#fff5a3}",
            ".sev.INFO{border-color:#40a9ff;color:#bfe3ff}",
            "</style>",
            "</head>",
            "<body>",
            "<header>",
            "<h1>s11r2 progress dashboard</h1>",
            f"<p class=\"sub\">Generated: {html.escape(now_utc.isoformat(timespec='seconds'))}</p>",
            f"<nav>{nav_links}</nav>",
            f"<div>{toc}</div>",
            "</header>",
            "<main>",
            '<div class="grid">',
            _render_validation_card(report),
            _render_legend_card(legend),
            *metric_cards,
            "</div>",
            "</main>",
            "</body>",
            "</html>",
        ]
    )


__all__ = [
    "DashboardLinks",
    "render_dashboard",
]
