# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from html import escape
from typing import Any, Final, cast

from typewiz.core.model_types import (
    DashboardView,
    OverrideEntry,
    ReadinessStatus,
    SeverityLevel,
    SummaryTabName,
)
from typewiz.core.summary_types import (
    HotspotsTab,
    OverviewTab,
    ReadinessTab,
    SummaryData,
    SummaryTabs,
)
from typewiz.core.type_aliases import CategoryKey
from typewiz.override_utils import get_override_components
from typewiz.readiness.compute import CATEGORY_LABELS

_TAB_ORDER: Final[tuple[SummaryTabName, ...]] = tuple(SummaryTabName)
_TAB_LABELS: Final[dict[SummaryTabName, str]] = {
    SummaryTabName.OVERVIEW: "Overview",
    SummaryTabName.ENGINES: "Engine Details",
    SummaryTabName.HOTSPOTS: "Hotspots",
    SummaryTabName.READINESS: "Readiness",
    SummaryTabName.RUNS: "Run Logs",
}


@dataclass
class _DashboardContext:
    summary: SummaryData
    view_choice: DashboardView
    tabs: SummaryTabs = field(init=False)
    overview: OverviewTab = field(init=False)
    severity_totals: Mapping[SeverityLevel, int] = field(init=False)
    category_totals: Mapping[CategoryKey, int] = field(init=False)
    run_summary: dict[str, dict[str, object]] = field(init=False)
    hotspots: HotspotsTab = field(init=False)
    readiness: ReadinessTab = field(init=False)
    engines: dict[str, dict[str, object]] = field(init=False)
    runs_tab: dict[str, dict[str, object]] = field(init=False)
    rule_files: dict[str, list[dict[str, object]]] = field(init=False)
    default_tab: str = field(init=False)

    def __post_init__(self) -> None:
        self.tabs = self.summary["tabs"]
        self.overview = self.tabs[SummaryTabName.OVERVIEW.value]
        self.severity_totals = self.overview["severityTotals"]
        self.category_totals = self.overview.get("categoryTotals", {})
        self.run_summary = cast(dict[str, dict[str, object]], self.overview["runSummary"])
        self.hotspots = self.tabs[SummaryTabName.HOTSPOTS.value]
        self.readiness = self.tabs[SummaryTabName.READINESS.value]
        engines_tab = self.tabs[SummaryTabName.ENGINES.value]
        runs_tab = self.tabs[SummaryTabName.RUNS.value]
        self.engines = cast(
            dict[str, dict[str, object]], engines_tab.get("runSummary", self.run_summary)
        )
        self.runs_tab = cast(
            dict[str, dict[str, object]], runs_tab.get("runSummary", self.run_summary)
        )
        self.rule_files = cast(
            dict[str, list[dict[str, object]]], self.hotspots.get("ruleFiles", {})
        )
        self.default_tab = self.view_choice.value

    def escape(self, value: object) -> str:
        return escape(str(value), quote=True)


def render_html(
    summary: SummaryData,
    *,
    default_view: DashboardView | str = DashboardView.OVERVIEW.value,
) -> str:
    view_choice = (
        default_view
        if isinstance(default_view, DashboardView)
        else DashboardView.from_str(default_view)
    )
    context = _DashboardContext(summary=summary, view_choice=view_choice)

    parts: list[str] = []
    parts.extend(_render_document_head(context))
    parts.extend(_render_tabs_navigation())
    parts.extend(_render_overview_tab(context))
    parts.extend(_render_engines_tab(context))
    parts.extend(_render_hotspots_tab(context))
    parts.extend(_render_readiness_tab(context))
    parts.extend(_render_runs_tab(context))
    parts.extend(_render_script_block())
    parts.append("</body>")
    parts.append("</html>")
    return "\n".join(parts) + "\n"


def _render_document_head(context: _DashboardContext) -> list[str]:
    h = context.escape
    return [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '  <meta charset="utf-8" />',
        "  <title>typewiz Dashboard</title>",
        "  <style>\n    :root{color-scheme:light dark;}\n    body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:2rem;background:#f5f5f5;color:#1f2330;}\n    h1,h2{color:#2b4b80;}\n    table{border-collapse:collapse;width:100%;margin-bottom:1.5rem;background:white;}\n    th,td{border:1px solid #d0d7e2;padding:0.5rem;text-align:left;}\n    th{background:#e8edf7;}\n    section{margin-bottom:2rem;}\n    .metrics{display:flex;flex-wrap:wrap;gap:1.5rem;}\n    .metric{background:white;border:1px solid #d0d7e2;padding:1rem;border-radius:6px;min-width:8rem;text-align:center;}\n    .metric strong{display:block;font-size:1.5rem;}\n    .tabs{display:flex;gap:0.75rem;margin:1.5rem 0;}\n    .tabs button{border:1px solid #2b4b80;background:white;color:#2b4b80;padding:0.45rem 1rem;border-radius:999px;cursor:pointer;font-weight:600;}\n    .tabs button.active{background:#2b4b80;color:white;}\n    .tab-pane{margin-top:1.5rem;}\n    .has-js .tab-pane{display:none;}\n    .has-js .tab-pane.active{display:block;}\n    .no-js .tabs{display:none;}\n    code{background:#eef1fb;padding:0.1rem 0.35rem;border-radius:4px;}\n    details{background:white;border:1px solid #d0d7e2;border-radius:8px;margin-bottom:1rem;padding:0.75rem;}\n    details[open]>summary{margin-bottom:0.5rem;}\n    summary{cursor:pointer;font-weight:600;}\n  </style>",
        "</head>",
        f'<body class="no-js" data-default-tab="{context.default_tab}">',
        "  <h1>typewiz Dashboard</h1>",
        f"  <p><strong>Generated:</strong> {h(context.summary['generatedAt'])}<br />",
        f"     <strong>Project root:</strong> {h(context.summary['projectRoot'])}</p>",
    ]


def _render_tabs_navigation() -> list[str]:
    lines = ['  <nav class="tabs" role="tablist">']
    lines.extend(
        f'    <button type="button" data-tab-target="{tab.value}" role="tab" aria-selected="false">{_TAB_LABELS[tab]}</button>'
        for tab in _TAB_ORDER
    )
    lines.append("  </nav>")
    return lines


def _overview_severity_section(severity: Mapping[SeverityLevel, int]) -> list[str]:
    return [
        "    <section>",
        "      <h2>Severity Totals</h2>",
        '      <div class="metrics">',
        f'        <div class="metric"><strong>{severity.get(SeverityLevel.ERROR, 0)}</strong>Errors</div>',
        f'        <div class="metric"><strong>{severity.get(SeverityLevel.WARNING, 0)}</strong>Warnings</div>',
        f'        <div class="metric"><strong>{severity.get(SeverityLevel.INFORMATION, 0)}</strong>Information</div>',
        "      </div>",
        "    </section>",
    ]


def _overview_run_summary_section(
    run_summary: Mapping[str, Mapping[str, object]],
    escape_fn: Callable[[object], str],
) -> list[str]:
    lines = [
        "    <section>",
        "      <h2>Run Summary</h2>",
        "      <table>",
        "        <thead><tr><th>Run</th><th>Errors</th><th>Warnings</th><th>Information</th><th>Total</th><th>Command</th></tr></thead>",
        "        <tbody>",
    ]
    if run_summary:
        lines.extend(_overview_run_rows(run_summary, escape_fn))
    else:
        lines.append('          <tr><td colspan="6"><em>No run data available</em></td></tr>')
    lines.extend(["        </tbody>", "      </table>", "    </section>"])
    return lines


def _overview_run_rows(
    run_summary: Mapping[str, Mapping[str, object]],
    escape_fn: Callable[[object], str],
) -> list[str]:
    rows: list[str] = []
    for key, data in run_summary.items():
        command_parts = _coerce_str_list(data.get("command"))
        cmd = " ".join(escape_fn(part) for part in command_parts)
        rows.append(
            "          <tr>"
            + f"<td>{escape_fn(key)}</td>"
            + f"<td>{data.get('errors', 0)}</td>"
            + f"<td>{data.get('warnings', 0)}</td>"
            + f"<td>{data.get('information', 0)}</td>"
            + f"<td>{data.get('total', 0)}</td>"
            + f"<td><code>{cmd}</code></td></tr>"
        )
    return rows


def _overview_category_section(
    categories: Mapping[CategoryKey, int],
    escape_fn: Callable[[object], str],
) -> list[str]:
    lines = [
        "    <section>",
        "      <h2>Category Totals</h2>",
        "      <table>",
        "        <thead><tr><th>Category</th><th>Total diagnostics</th></tr></thead>",
        "        <tbody>",
    ]
    if categories:
        lines.extend([
            f"          <tr><td>{escape_fn(key)}</td><td>{value}</td></tr>"
            for key, value in categories.items()
        ])
    else:
        lines.append('          <tr><td colspan="2"><em>No categories recorded</em></td></tr>')
    lines.extend(["        </tbody>", "      </table>", "    </section>"])
    return lines


def _render_overview_tab(context: _DashboardContext) -> list[str]:
    lines = ['  <section class="tab-pane" data-tab-pane="overview">']
    lines.extend(_overview_severity_section(context.severity_totals))
    lines.extend(_overview_run_summary_section(context.run_summary, context.escape))
    lines.extend(_overview_category_section(context.category_totals, context.escape))
    lines.append("  </section>")
    return lines


def _render_engines_tab(context: _DashboardContext) -> list[str]:
    lines = ['  <section class="tab-pane" data-tab-pane="engines">', "    <h2>Engine Details</h2>"]
    if context.engines:
        lines.extend(_engine_table_section(context))
    else:
        lines.append("    <p>No engine data recorded.</p>")
    lines.append("  </section>")
    return lines


def _engine_table_section(context: _DashboardContext) -> list[str]:
    lines = [
        "    <section>",
        "      <table>",
        "        <thead><tr><th>Run</th><th>Profile</th><th>Config file</th><th>Plugin args</th><th>Include</th><th>Exclude</th><th>Overrides</th></tr></thead>",
        "        <tbody>",
    ]
    lines.extend(_engine_rows(context))
    lines.extend(["        </tbody>", "      </table>", "    </section>"])
    return lines


def _engine_rows(context: _DashboardContext) -> list[str]:
    h = context.escape
    rows: list[str] = []
    for key, data in context.engines.items():
        engine_options = _as_mapping(data.get("engineOptions", {}))
        plugin_args = ", ".join(
            h(arg) for arg in _coerce_str_list(engine_options.get("pluginArgs"))
        )
        include_paths = ", ".join(
            h(path) for path in _coerce_str_list(engine_options.get("include"))
        )
        exclude_paths = ", ".join(
            h(path) for path in _coerce_str_list(engine_options.get("exclude"))
        )
        override_summaries = [
            _summarise_override_entry(entry, h)
            for entry in _coerce_override_list(engine_options.get("overrides"))
        ]
        rows.append(
            "          <tr>"
            + f"<td>{h(key)}</td>"
            + f"<td>{h(str(engine_options.get('profile')))}</td>"
            + f"<td>{h(str(engine_options.get('configFile')))}</td>"
            + f"<td>{plugin_args}</td>"
            + f"<td>{include_paths}</td>"
            + f"<td>{exclude_paths}</td>"
            + f"<td>{h('; '.join(override_summaries))}</td>"
            + "</tr>"
        )
    return rows


def _render_hotspots_tab(context: _DashboardContext) -> list[str]:
    lines = [
        '  <section class="tab-pane" data-tab-pane="hotspots">',
        "    <h2>Hotspots</h2>",
    ]
    lines.extend(_render_rule_hotspot_table(context))
    lines.extend(_render_folder_hotspot_table(context))
    lines.extend(_render_file_hotspot_table(context))
    lines.extend(_render_rule_file_details(context))
    lines.append("  </section>")
    return lines


def _render_rule_hotspot_table(context: _DashboardContext) -> list[str]:
    h = context.escape
    top_rules = context.hotspots["topRules"]
    lines = [
        "    <section>",
        "      <h3>Top Rules</h3>",
        "      <table>",
        "        <thead><tr><th>Rule</th><th>Occurrences</th></tr></thead><tbody>",
    ]
    if top_rules:
        for rule, count in top_rules.items():
            lines.append(f"          <tr><td><code>{h(rule)}</code></td><td>{count}</td></tr>")
    else:
        lines.append('          <tr><td colspan="2"><em>No rules recorded</em></td></tr>')
    lines.extend(["        </tbody>", "      </table>", "    </section>"])
    return lines


def _render_folder_hotspot_table(context: _DashboardContext) -> list[str]:
    h = context.escape
    top_folders = context.hotspots["topFolders"]
    lines = [
        "    <section>",
        "      <h3>Top Folder Hotspots</h3>",
        "      <table>",
        "        <thead><tr><th>Folder</th><th>Errors</th><th>Warnings</th><th>Information</th><th>Runs</th></tr></thead><tbody>",
    ]
    if top_folders:
        for folder in top_folders:
            lines.append(
                f"          <tr><td>{h(folder['path'])}</td><td>{folder['errors']}</td><td>{folder['warnings']}</td><td>{folder['information']}</td><td>{folder['participatingRuns']}</td></tr>"
            )
    else:
        lines.append('          <tr><td colspan="5"><em>No folder hotspots</em></td></tr>')
    lines.extend(["        </tbody>", "      </table>", "    </section>"])
    return lines


def _render_file_hotspot_table(context: _DashboardContext) -> list[str]:
    h = context.escape
    top_files = context.hotspots["topFiles"]
    lines = [
        "    <section>",
        "      <h3>Top File Hotspots</h3>",
        "      <table>",
        "        <thead><tr><th>File</th><th>Errors</th><th>Warnings</th></tr></thead><tbody>",
    ]
    if top_files:
        for file_entry in top_files:
            lines.append(
                f"          <tr><td>{h(file_entry['path'])}</td><td>{file_entry['errors']}</td><td>{file_entry['warnings']}</td></tr>"
            )
    else:
        lines.append('          <tr><td colspan="3"><em>No file hotspots</em></td></tr>')
    lines.extend(["        </tbody>", "      </table>", "    </section>"])
    return lines


def _render_rule_file_details(context: _DashboardContext) -> list[str]:
    h = context.escape
    rule_files = context.rule_files
    lines = ["    <section>", "      <h3>Rule hotspots by file</h3>"]
    if rule_files:
        for rule, rule_entries in rule_files.items():
            lines.append(f"      <details><summary><code>{h(rule)}</code></summary><ul>")
            if rule_entries:
                for rule_entry in rule_entries[:10]:
                    path = rule_entry.get("path", "<unknown>")
                    count = rule_entry.get("count", 0)
                    lines.append(f"        <li><code>{h(str(path))}</code> ({count})</li>")
            else:
                lines.append("        <li><em>No matching paths</em></li>")
            lines.append("      </ul></details>")
    else:
        lines.append("      <p>No rule hotspot breakdown available.</p>")
    lines.append("    </section>")
    return lines


def _summarise_override_entry(entry: OverrideEntry, escape_fn: Callable[[str], str]) -> str:
    path, profile, plugin_args, include_paths, exclude_paths = get_override_components(entry)
    details: list[str] = []
    if profile:
        details.append(f"profile={escape_fn(profile)}")
    if plugin_args:
        details.append("args=" + "/".join(escape_fn(str(arg)) for arg in plugin_args))
    if include_paths:
        details.append("include=" + "/".join(escape_fn(str(path)) for path in include_paths))
    if exclude_paths:
        details.append("exclude=" + "/".join(escape_fn(str(path)) for path in exclude_paths))
    summary = escape_fn(path)
    if details:
        summary = f"{summary} ({', '.join(details)})"
    return summary


def _coerce_str_list(value: object) -> list[str]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        items = cast(Sequence[object], value)
        return [str(item) for item in items]
    return []


def _coerce_override_list(value: object) -> list[OverrideEntry]:
    entries: list[OverrideEntry] = []
    if isinstance(value, Sequence):
        for entry in cast(Sequence[object], value):
            if isinstance(entry, dict):
                entries.append(cast(OverrideEntry, entry))
    return entries


def _as_mapping(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return cast(dict[str, Any], value)
    return cast(dict[str, Any], {})


def _render_readiness_tab(context: _DashboardContext) -> list[str]:
    h = context.escape
    readiness = context.readiness
    strict = cast(dict[ReadinessStatus, list[dict[str, object]]], readiness.get("strict", {}))
    ready_list = strict.get(ReadinessStatus.READY, [])
    close_list = strict.get(ReadinessStatus.CLOSE, [])
    blocked_list = strict.get(ReadinessStatus.BLOCKED, [])
    lines = [
        '  <section class="tab-pane" data-tab-pane="readiness">',
        "    <h2>Strict Typing Readiness</h2>",
        '    <div class="metrics">',
        f'      <div class="metric"><strong>{len(ready_list)}</strong>Ready</div>',
        f'      <div class="metric"><strong>{len(close_list)}</strong>Close</div>',
        f'      <div class="metric"><strong>{len(blocked_list)}</strong>Blocked</div>',
        "    </div>",
    ]

    def _render_strict_entries(label: str, entries: list[dict[str, object]]) -> None:
        if not entries:
            lines.append(f"    <p><strong>{label}:</strong> none</p>")
            return
        lines.append(
            f"    <details open><summary><strong>{label}</strong> ({len(entries)})</summary>",
        )
        lines.append("      <ul>")
        for entry in entries[:12]:
            notes_list = cast(list[str], entry.get("notes") or entry.get("recommendations") or [])
            note_text = f" — {', '.join(notes_list)}" if notes_list else ""
            lines.append(
                f"        <li><code>{h(str(entry['path']))}</code> (diagnostics={entry.get('diagnostics', 0)}){note_text}</li>",
            )
        if len(entries) > 12:
            lines.append(f"        <li>… plus {len(entries) - 12} more</li>")
        lines.append("      </ul>")
        lines.append("    </details>")

    _render_strict_entries("Strict-ready folders", ready_list)
    _render_strict_entries("Close to strict", close_list)
    _render_strict_entries("Blocked", blocked_list)

    readiness_options = readiness.get("options", {})
    if readiness_options:
        lines.append("    <section>")
        lines.append("      <h3>Per-option readiness</h3>")
        lines.append(
            "      <table><thead><tr><th>Option</th><th>Ready</th><th>Close</th><th>Blocked</th><th>Close threshold</th></tr></thead><tbody>",
        )
        label_lookup = cast(dict[str, str], CATEGORY_LABELS)
        for category, payload in readiness_options.items():
            label_key = str(category)
            label = label_lookup.get(label_key, label_key)
            bucket_map = payload.get("buckets", {})
            ready_entries = bucket_map.get(ReadinessStatus.READY, ())
            close_entries = bucket_map.get(ReadinessStatus.CLOSE, ())
            blocked_entries = bucket_map.get(ReadinessStatus.BLOCKED, ())
            threshold = int(payload.get("threshold", 0))
            lines.append(
                (
                    f"        <tr><td>{h(label)}</td>"
                    f"<td>{len(ready_entries)}</td>"
                    f"<td>{len(close_entries)}</td>"
                    f"<td>{len(blocked_entries)}</td>"
                    f"<td>{threshold}</td></tr>"
                ),
            )
        lines.extend(["      </tbody></table>", "    </section>"])
    else:
        lines.append("    <p>No readiness data available.</p>")
    lines.append("  </section>")
    return lines


def _render_runs_tab(context: _DashboardContext) -> list[str]:
    h = context.escape
    run_details = context.runs_tab or context.run_summary
    lines = ['  <section class="tab-pane" data-tab-pane="runs">', "    <h2>Run Logs</h2>"]
    if run_details:
        for key, data in run_details.items():
            breakdown = data.get("severityBreakdown", {})
            command_items = _coerce_str_list(data.get("command"))
            cmd = " ".join(h(part) for part in command_items)
            lines.extend(
                [
                    '    <details class="run-log" open>',
                    f"      <summary><strong>{h(key)}</strong> · command: <code>{cmd}</code></summary>",
                    "      <ul>",
                    f"        <li>Errors: {data.get('errors', 0)}</li>",
                    f"        <li>Warnings: {data.get('warnings', 0)}</li>",
                    f"        <li>Information: {data.get('information', 0)}</li>",
                    f"        <li>Total diagnostics: {data.get('total', 0)}</li>",
                    f"        <li>Severity breakdown: {breakdown or {}}</li>",
                    "      </ul>",
                    "    </details>",
                ],
            )
    else:
        lines.append("    <p>No runs recorded.</p>")
    lines.append("  </section>")
    return lines


def _render_script_block() -> list[str]:
    return [
        "  <script>\n    (function(){\n      const body=document.body;\n      body.classList.remove('no-js');\n      body.classList.add('has-js');\n      const storageKey='typewiz-dashboard-tab';\n      const tabs=Array.from(document.querySelectorAll('[data-tab-target]'));\n      const panes=Array.from(document.querySelectorAll('[data-tab-pane]'));\n      function activate(name){\n        tabs.forEach(btn=>{const active=btn.dataset.tabTarget===name;btn.classList.toggle('active',active);btn.setAttribute('aria-selected',String(active));});\n        panes.forEach(pane=>pane.classList.toggle('active',pane.dataset.tabPane===name));\n      }\n      let stored=null;\n      try{stored=window.localStorage.getItem(storageKey);}catch(_){}\n      const initial=tabs.some(btn=>btn.dataset.tabTarget===stored) ? stored : body.dataset.defaultTab || 'overview';\n      activate(initial);\n      tabs.forEach(btn=>btn.addEventListener('click',()=>{const name=btn.dataset.tabTarget;activate(name);try{window.localStorage.setItem(storageKey,name);}catch(_){};}));\n    })();\n  </script>",
    ]
