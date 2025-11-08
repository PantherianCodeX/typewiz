# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

from collections.abc import Sequence
from html import escape
from typing import Final, cast

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
from typewiz.core.type_aliases import RelPath
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


def render_html(  # noqa: C901, PLR0912, PLR0915
    summary: SummaryData,
    *,
    default_view: DashboardView | str = DashboardView.OVERVIEW.value,
) -> str:
    view_choice = (
        default_view
        if isinstance(default_view, DashboardView)
        else DashboardView.from_str(default_view)
    )
    default_view_value = view_choice.value

    def h(text: str) -> str:
        return escape(text, quote=True)

    tabs: SummaryTabs = summary["tabs"]
    overview: OverviewTab = tabs[SummaryTabName.OVERVIEW.value]
    run_summary = overview["runSummary"]
    severity = overview["severityTotals"]
    hotspots: HotspotsTab = tabs[SummaryTabName.HOTSPOTS.value]
    readiness: ReadinessTab = tabs[SummaryTabName.READINESS.value]

    top_rules = hotspots["topRules"]
    top_folders = hotspots["topFolders"]
    top_files = hotspots["topFiles"]

    parts: list[str] = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '  <meta charset="utf-8" />',
        "  <title>typewiz Dashboard</title>",
        "  <style>\n    :root{color-scheme:light dark;}\n    body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:2rem;background:#f5f5f5;color:#1f2330;}\n    h1,h2{color:#2b4b80;}\n    table{border-collapse:collapse;width:100%;margin-bottom:1.5rem;background:white;}\n    th,td{border:1px solid #d0d7e2;padding:0.5rem;text-align:left;}\n    th{background:#e8edf7;}\n    section{margin-bottom:2rem;}\n    .metrics{display:flex;flex-wrap:wrap;gap:1.5rem;}\n    .metric{background:white;border:1px solid #d0d7e2;padding:1rem;border-radius:6px;min-width:8rem;text-align:center;}\n    .metric strong{display:block;font-size:1.5rem;}\n    .tabs{display:flex;gap:0.75rem;margin:1.5rem 0;}\n    .tabs button{border:1px solid #2b4b80;background:white;color:#2b4b80;padding:0.45rem 1rem;border-radius:999px;cursor:pointer;font-weight:600;}\n    .tabs button.active{background:#2b4b80;color:white;}\n    .tab-pane{margin-top:1.5rem;}\n    .has-js .tab-pane{display:none;}\n    .has-js .tab-pane.active{display:block;}\n    .no-js .tabs{display:none;}\n    code{background:#eef1fb;padding:0.1rem 0.35rem;border-radius:4px;}\n    details{background:white;border:1px solid #d0d7e2;border-radius:8px;margin-bottom:1rem;padding:0.75rem;}\n    details[open]>summary{margin-bottom:0.5rem;}\n    summary{cursor:pointer;font-weight:600;}\n  </style>",
        "</head>",
        f'<body class="no-js" data-default-tab="{default_view_value}">',
        "  <h1>typewiz Dashboard</h1>",
        f"  <p><strong>Generated:</strong> {h(str(summary['generatedAt']))}<br />",
        f"     <strong>Project root:</strong> {h(str(summary['projectRoot']))}</p>",
        '  <nav class="tabs" role="tablist">',
    ]

    parts.extend(
        f'    <button type="button" data-tab-target="{tab.value}" role="tab" aria-selected="false">{_TAB_LABELS[tab]}</button>'
        for tab in _TAB_ORDER
    )
    parts.append("  </nav>")

    # Overview tab
    parts.extend(
        [
            '  <section class="tab-pane" data-tab-pane="overview">',
            "    <section>",
            "      <h2>Severity Totals</h2>",
            '      <div class="metrics">',
            f'        <div class="metric"><strong>{severity.get(SeverityLevel.ERROR, 0)}</strong>Errors</div>',
            f'        <div class="metric"><strong>{severity.get(SeverityLevel.WARNING, 0)}</strong>Warnings</div>',
            f'        <div class="metric"><strong>{severity.get(SeverityLevel.INFORMATION, 0)}</strong>Information</div>',
            "      </div>",
            "    </section>",
            "    <section>",
            "      <h2>Run Summary</h2>",
            "      <table>",
            "        <thead><tr><th>Run</th><th>Errors</th><th>Warnings</th><th>Information</th><th>Total</th><th>Command</th></tr></thead>",
            "        <tbody>",
        ],
    )
    if run_summary:
        for key, data in run_summary.items():
            cmd = " ".join(h(part) for part in data.get("command", []))
            parts.append(
                (
                    f"          <tr><td>{h(key)}</td>"
                    f"<td>{data.get('errors', 0)}</td>"
                    f"<td>{data.get('warnings', 0)}</td>"
                    f"<td>{data.get('information', 0)}</td>"
                    f"<td>{data.get('total', 0)}</td>"
                    f"<td><code>{cmd}</code></td></tr>"
                ),
            )
    else:
        parts.append('          <tr><td colspan="6"><em>No runs recorded</em></td></tr>')
    parts.extend(
        [
            "        </tbody>",
            "      </table>",
            "    </section>",
            "  </section>",
        ],
    )

    def _as_code_list(items: Sequence[str | RelPath]) -> str:
        if not items:
            return "—"
        return " ".join(f"<code>{h(str(item))}</code>" for item in items)

    # Engine details tab
    parts.append('  <section class="tab-pane" data-tab-pane="engines">')
    parts.append("    <h2>Engine Details</h2>")
    if run_summary:
        for key, data in run_summary.items():
            options = data.get("engineOptions", {}) or {}
            profile_value = options.get("profile")
            config_value = options.get("configFile")
            plugin_args = options.get("pluginArgs", []) or []
            include = options.get("include", []) or []
            exclude = options.get("exclude", []) or []
            overrides: list[OverrideEntry] = options.get("overrides", []) or []
            profile_display = f"<code>{h(str(profile_value))}</code>" if profile_value else "—"
            config_display = f"<code>{h(str(config_value))}</code>" if config_value else "—"
            parts.extend(
                [
                    '    <details class="engine-options" open>',
                    f"      <summary><strong>{h(key)}</strong></summary>",
                    "      <ul>",
                    f"        <li>Profile: {profile_display}</li>",
                    f"        <li>Config file: {config_display}</li>",
                    f"        <li>Plugin args: {_as_code_list(plugin_args)}</li>",
                    f"        <li>Include paths: {_as_code_list(include)}</li>",
                    f"        <li>Exclude paths: {_as_code_list(exclude)}</li>",
                ],
            )
            if overrides:
                parts.append("        <li>Folder overrides:<ul>")
                for entry in overrides:
                    path, profile, plugin_args, include_paths, exclude_paths = (
                        get_override_components(entry)
                    )
                    detail_bits: list[str] = []
                    if profile:
                        detail_bits.append(f"profile=<code>{h(profile)}</code>")
                    if plugin_args:
                        detail_bits.append(
                            "plugin args="
                            + " ".join(f"<code>{h(arg)}</code>" for arg in plugin_args),
                        )
                    if include_paths:
                        detail_bits.append(
                            "include="
                            + " ".join(f"<code>{h(item)}</code>" for item in include_paths),
                        )
                    if exclude_paths:
                        detail_bits.append(
                            "exclude="
                            + " ".join(f"<code>{h(item)}</code>" for item in exclude_paths),
                        )
                    if not detail_bits:
                        detail_bits.append("no explicit changes")
                    details_html = "; ".join(detail_bits)
                    parts.append(f"          <li><code>{h(path)}</code>: {details_html}</li>")
                parts.append("        </ul></li>")
            parts.extend(
                [
                    "      </ul>",
                    "    </details>",
                ],
            )
            # Optional: display raw tool totals if present, and indicate mismatch with parsed counts.
            tool_totals = data.get("toolSummary")
            if isinstance(tool_totals, dict) and tool_totals:
                t_errors = int(tool_totals.get("errors", 0))
                t_warnings = int(tool_totals.get("warnings", 0))
                t_info = int(tool_totals.get("information", 0))
                t_total = int(tool_totals.get("total", t_errors + t_warnings + t_info))
                p_errors = int(data.get("errors", 0))
                p_warnings = int(data.get("warnings", 0))
                p_info = int(data.get("information", 0))
                p_total = int(data.get("total", p_errors + p_warnings + p_info))
                mismatch = t_errors != p_errors or t_warnings != p_warnings or t_total != p_total
                mismatch_note = (
                    f" <em>(mismatch vs parsed: {p_errors}/{p_warnings}/{p_info} total={p_total})</em>"
                    if mismatch
                    else ""
                )
                parts.append(
                    f"    <p><strong>Tool totals:</strong> errors={t_errors}, warnings={t_warnings}, information={t_info}, total={t_total}{mismatch_note}</p>",
                )
    else:
        parts.append("    <p>No engine data available.</p>")
    parts.append("  </section>")

    # Hotspots tab
    parts.append('  <section class="tab-pane" data-tab-pane="hotspots">')
    parts.append("    <h2>Hotspots</h2>")
    if top_rules:
        parts.extend(
            [
                "    <section>",
                "      <h3>Common Diagnostic Rules</h3>",
                "      <table>",
                "        <thead><tr><th>Rule</th><th>Count</th></tr></thead><tbody>",
            ],
        )
        parts.extend(
            f"          <tr><td><code>{h(rule)}</code></td><td>{count}</td></tr>"
            for rule, count in top_rules.items()
        )
        parts.extend(["        </tbody>", "      </table>", "    </section>"])
    else:
        parts.append("    <p>No diagnostic rules recorded.</p>")

    parts.extend(
        [
            "    <section>",
            "      <h3>Top Folder Hotspots</h3>",
            "      <table>",
            "        <thead><tr><th>Folder</th><th>Errors</th><th>Warnings</th><th>Information</th><th>Runs</th></tr></thead><tbody>",
        ],
    )
    if top_folders:
        parts.extend(
            f"          <tr><td>{h(folder['path'])}</td><td>{folder['errors']}</td><td>{folder['warnings']}</td><td>{folder['information']}</td><td>{folder['participatingRuns']}</td></tr>"
            for folder in top_folders
        )
    else:
        parts.append('          <tr><td colspan="5"><em>No folder hotspots</em></td></tr>')
    parts.extend(["        </tbody>", "      </table>", "    </section>"])

    parts.extend(
        [
            "    <section>",
            "      <h3>Top File Hotspots</h3>",
            "      <table>",
            "        <thead><tr><th>File</th><th>Errors</th><th>Warnings</th></tr></thead><tbody>",
        ],
    )
    if top_files:
        parts.extend(
            f"          <tr><td>{h(file_entry['path'])}</td><td>{file_entry['errors']}</td><td>{file_entry['warnings']}</td></tr>"
            for file_entry in top_files
        )
    else:
        parts.append('          <tr><td colspan="3"><em>No file hotspots</em></td></tr>')
    parts.extend(["        </tbody>", "      </table>", "    </section>"])
    rule_files = hotspots.get("ruleFiles", {})
    parts.append("    <section>")
    parts.append("      <h3>Rule hotspots by file</h3>")
    if rule_files:
        for rule, rule_entries in rule_files.items():
            parts.append(
                f"      <details><summary><code>{h(rule)}</code></summary><ul>",
            )
            if rule_entries:
                for rule_entry in rule_entries[:10]:
                    path = rule_entry.get("path", "<unknown>")
                    count = rule_entry.get("count", 0)
                    parts.append(f"        <li><code>{h(str(path))}</code> ({count})</li>")
            else:
                parts.append("        <li><em>No matching paths</em></li>")
            parts.append("      </ul></details>")
    else:
        parts.append("      <p>No rule hotspot breakdown available.</p>")
    parts.append("    </section>")
    parts.append("  </section>")

    # Readiness tab
    parts.append('  <section class="tab-pane" data-tab-pane="readiness">')
    parts.append("    <h2>Strict Typing Readiness</h2>")
    strict = cast(dict[ReadinessStatus, list[dict[str, object]]], readiness.get("strict", {}))
    ready_list = strict.get(ReadinessStatus.READY, [])
    close_list = strict.get(ReadinessStatus.CLOSE, [])
    blocked_list = strict.get(ReadinessStatus.BLOCKED, [])
    parts.extend(
        [
            '    <div class="metrics">',
            f'      <div class="metric"><strong>{len(ready_list)}</strong>Ready</div>',
            f'      <div class="metric"><strong>{len(close_list)}</strong>Close</div>',
            f'      <div class="metric"><strong>{len(blocked_list)}</strong>Blocked</div>',
            "    </div>",
        ],
    )

    def _render_strict_entries(label: str, entries: list[dict[str, object]]) -> None:
        if not entries:
            parts.append(f"    <p><strong>{label}:</strong> none</p>")
            return
        parts.append(
            f"    <details open><summary><strong>{label}</strong> ({len(entries)})</summary>",
        )
        parts.append("      <ul>")
        for entry in entries[:12]:
            notes_list = cast(list[str], entry.get("notes") or entry.get("recommendations") or [])
            note_text = f" — {', '.join(notes_list)}" if notes_list else ""
            parts.append(
                f"        <li><code>{h(str(entry['path']))}</code> (diagnostics={entry['diagnostics']}){note_text}</li>",
            )
        if len(entries) > 12:
            parts.append(f"        <li>… plus {len(entries) - 12} more</li>")
        parts.append("      </ul>")
        parts.append("    </details>")

    _render_strict_entries("Strict-ready folders", ready_list)
    _render_strict_entries("Close to strict", close_list)
    _render_strict_entries("Blocked", blocked_list)

    readiness_options = readiness.get("options", {})
    if readiness_options:
        parts.append("    <section>")
        parts.append("      <h3>Per-option readiness</h3>")
        parts.append(
            "      <table><thead><tr><th>Option</th><th>Ready</th><th>Close</th><th>Blocked</th><th>Close threshold</th></tr></thead><tbody>",
        )
        label_lookup = cast(dict[str, str], CATEGORY_LABELS)
        for category, payload in readiness_options.items():
            label_key: str = str(category)
            label = label_lookup.get(label_key, label_key)
            bucket_map = payload.get("buckets", {})
            ready_entries = bucket_map.get(ReadinessStatus.READY, ())
            close_entries = bucket_map.get(ReadinessStatus.CLOSE, ())
            blocked_entries = bucket_map.get(ReadinessStatus.BLOCKED, ())
            threshold = int(payload.get("threshold", 0))
            parts.append(
                (
                    f"        <tr><td>{h(label)}</td>"
                    f"<td>{len(ready_entries)}</td>"
                    f"<td>{len(close_entries)}</td>"
                    f"<td>{len(blocked_entries)}</td>"
                    f"<td>{threshold}</td></tr>"
                ),
            )
        parts.extend(["      </tbody></table>", "    </section>"])
    else:
        parts.append("    <p>No readiness data available.</p>")
    parts.append("  </section>")

    # Runs tab
    parts.append('  <section class="tab-pane" data-tab-pane="runs">')
    parts.append("    <h2>Run Logs</h2>")
    runs_tab = tabs[SummaryTabName.RUNS.value]
    run_details = runs_tab.get("runSummary", run_summary)
    if run_details:
        for key, data in run_details.items():
            breakdown = data.get("severityBreakdown", {})
            cmd = " ".join(h(str(part)) for part in data.get("command", []))
            parts.extend(
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
        parts.append("    <p>No runs recorded.</p>")
    parts.append("  </section>")

    parts.extend(
        [
            "  <script>\n    (function(){\n      const body=document.body;\n      body.classList.remove('no-js');\n      body.classList.add('has-js');\n      const storageKey='typewiz-dashboard-tab';\n      const tabs=Array.from(document.querySelectorAll('[data-tab-target]'));\n      const panes=Array.from(document.querySelectorAll('[data-tab-pane]'));\n      function activate(name){\n        tabs.forEach(btn=>{const active=btn.dataset.tabTarget===name;btn.classList.toggle('active',active);btn.setAttribute('aria-selected',String(active));});\n        panes.forEach(pane=>pane.classList.toggle('active',pane.dataset.tabPane===name));\n      }\n      let stored=null;\n      try{stored=window.localStorage.getItem(storageKey);}catch(_){}\n      const initial=tabs.some(btn=>btn.dataset.tabTarget===stored) ? stored : body.dataset.defaultTab || 'overview';\n      activate(initial);\n      tabs.forEach(btn=>btn.addEventListener('click',()=>{const name=btn.dataset.tabTarget;activate(name);try{window.localStorage.setItem(storageKey,name);}catch(_){};}));\n    })();\n  </script>",
            "</body>",
            "</html>",
        ],
    )

    return "\n".join(parts) + "\n"
