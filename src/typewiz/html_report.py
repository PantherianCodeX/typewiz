from __future__ import annotations

from html import escape
from typing import Any
from .readiness import CATEGORY_LABELS

_TAB_ORDER = ("overview", "engines", "hotspots", "readiness", "runs")
_TAB_LABELS = {
    "overview": "Overview",
    "engines": "Engine Details",
    "hotspots": "Hotspots",
    "readiness": "Readiness",
    "runs": "Run Logs",
}


def render_html(summary: dict[str, Any], *, default_view: str = "overview") -> str:
    default_view = default_view if default_view in _TAB_ORDER else "overview"

    def h(text: str) -> str:
        return escape(text, quote=True)

    tabs = summary.get("tabs", {})
    overview = tabs.get("overview", {})
    run_summary = overview.get("runSummary", summary.get("runSummary", {}))
    severity = overview.get("severityTotals", summary.get("severityTotals", {}))
    hotspots = tabs.get("hotspots", {})
    readiness = tabs.get("readiness", {})

    top_rules = hotspots.get("topRules", summary.get("topRules", {}))
    top_folders = hotspots.get("topFolders", summary.get("topFolders", []))
    top_files = hotspots.get("topFiles", summary.get("topFiles", []))

    parts: list[str] = [
        "<!DOCTYPE html>",
        "<html lang=\"en\">",
        "<head>",
        "  <meta charset=\"utf-8\" />",
        "  <title>typewiz Dashboard</title>",
        "  <style>\n    :root{color-scheme:light dark;}\n    body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:2rem;background:#f5f5f5;color:#1f2330;}\n    h1,h2{color:#2b4b80;}\n    table{border-collapse:collapse;width:100%;margin-bottom:1.5rem;background:white;}\n    th,td{border:1px solid #d0d7e2;padding:0.5rem;text-align:left;}\n    th{background:#e8edf7;}\n    section{margin-bottom:2rem;}\n    .metrics{display:flex;flex-wrap:wrap;gap:1.5rem;}\n    .metric{background:white;border:1px solid #d0d7e2;padding:1rem;border-radius:6px;min-width:8rem;text-align:center;}\n    .metric strong{display:block;font-size:1.5rem;}\n    .tabs{display:flex;gap:0.75rem;margin:1.5rem 0;}\n    .tabs button{border:1px solid #2b4b80;background:white;color:#2b4b80;padding:0.45rem 1rem;border-radius:999px;cursor:pointer;font-weight:600;}\n    .tabs button.active{background:#2b4b80;color:white;}\n    .tab-pane{margin-top:1.5rem;}\n    .has-js .tab-pane{display:none;}\n    .has-js .tab-pane.active{display:block;}\n    .no-js .tabs{display:none;}\n    code{background:#eef1fb;padding:0.1rem 0.35rem;border-radius:4px;}\n    details{background:white;border:1px solid #d0d7e2;border-radius:8px;margin-bottom:1rem;padding:0.75rem;}\n    details[open]>summary{margin-bottom:0.5rem;}\n    summary{cursor:pointer;font-weight:600;}\n  </style>",
        "</head>",
        f"<body class=\"no-js\" data-default-tab=\"{default_view}\">",
        "  <h1>typewiz Dashboard</h1>",
        f"  <p><strong>Generated:</strong> {h(str(summary.get('generatedAt', 'unknown')))}<br />",
        f"     <strong>Project root:</strong> {h(str(summary.get('projectRoot', '')))}</p>",
        "  <nav class=\"tabs\" role=\"tablist\">",
    ]

    for tab in _TAB_ORDER:
        parts.append(
            f"    <button type=\"button\" data-tab-target=\"{tab}\" role=\"tab\" aria-selected=\"false\">{_TAB_LABELS[tab]}</button>"
        )
    parts.append("  </nav>")

    # Overview tab
    parts.extend(
        [
            "  <section class=\"tab-pane\" data-tab-pane=\"overview\">",
            "    <section>",
            "      <h2>Severity Totals</h2>",
            "      <div class=\"metrics\">",
            f"        <div class=\"metric\"><strong>{severity.get('error', 0)}</strong>Errors</div>",
            f"        <div class=\"metric\"><strong>{severity.get('warning', 0)}</strong>Warnings</div>",
            f"        <div class=\"metric\"><strong>{severity.get('information', 0)}</strong>Information</div>",
            "      </div>",
            "    </section>",
            "    <section>",
            "      <h2>Run Summary</h2>",
            "      <table>",
            "        <thead><tr><th>Run</th><th>Errors</th><th>Warnings</th><th>Information</th><th>Total</th><th>Command</th></tr></thead>",
            "        <tbody>",
        ]
    )
    if run_summary:
        for key, data in run_summary.items():
            cmd = " ".join(h(str(part)) for part in data.get("command", []))
            parts.append(
                "          <tr>"
                f"<td>{h(key)}</td>"
                f"<td>{data.get('errors', 0)}</td>"
                f"<td>{data.get('warnings', 0)}</td>"
                f"<td>{data.get('information', 0)}</td>"
                f"<td>{data.get('total', 0)}</td>"
                f"<td><code>{cmd}</code></td>"
                "</tr>"
            )
    else:
        parts.append("          <tr><td colspan=\"6\"><em>No runs recorded</em></td></tr>")
    parts.extend(
        [
            "        </tbody>",
            "      </table>",
            "    </section>",
            "  </section>",
        ]
    )

    def _as_code_list(items: list[str]) -> str:
        if not items:
            return "—"
        return " ".join(f"<code>{h(str(item))}</code>" for item in items)

    # Engine details tab
    parts.append("  <section class=\"tab-pane\" data-tab-pane=\"engines\">")
    parts.append("    <h2>Engine Details</h2>")
    if run_summary:
        for key, data in run_summary.items():
            options = data.get("engineOptions", {}) or {}
            profile_value = options.get("profile")
            config_value = options.get("configFile")
            plugin_args = [str(arg) for arg in options.get("pluginArgs", []) or []]
            include = [str(item) for item in options.get("include", []) or []]
            exclude = [str(item) for item in options.get("exclude", []) or []]
            overrides = [dict(item) for item in options.get("overrides", []) or []]
            profile_display = f"<code>{h(str(profile_value))}</code>" if profile_value else "—"
            config_display = f"<code>{h(str(config_value))}</code>" if config_value else "—"
            parts.extend(
                [
                    "    <details class=\"engine-options\" open>",
                    f"      <summary><strong>{h(key)}</strong></summary>",
                    "      <ul>",
                    f"        <li>Profile: {profile_display}</li>",
                    f"        <li>Config file: {config_display}</li>",
                    f"        <li>Plugin args: {_as_code_list(plugin_args)}</li>",
                    f"        <li>Include paths: {_as_code_list(include)}</li>",
                    f"        <li>Exclude paths: {_as_code_list(exclude)}</li>",
                ]
            )
            if overrides:
                parts.append("        <li>Folder overrides:<ul>")
                for entry in overrides:
                    path = h(str(entry.get("path", "—")))
                    detail_bits: list[str] = []
                    if entry.get("profile"):
                        detail_bits.append(f"profile=<code>{h(str(entry['profile']))}</code>")
                    if entry.get("pluginArgs"):
                        detail_bits.append(
                            "plugin args="
                            + " ".join(f"<code>{h(str(arg))}</code>" for arg in entry.get("pluginArgs", []))
                        )
                    if entry.get("include"):
                        detail_bits.append(
                            "include="
                            + " ".join(f"<code>{h(str(item))}</code>" for item in entry.get("include", []))
                        )
                    if entry.get("exclude"):
                        detail_bits.append(
                            "exclude="
                            + " ".join(f"<code>{h(str(item))}</code>" for item in entry.get("exclude", []))
                        )
                    if not detail_bits:
                        detail_bits.append("no explicit changes")
                    parts.append(f"          <li><code>{path}</code>: {'; '.join(detail_bits)}</li>")
                parts.append("        </ul></li>")
            parts.extend([
                "      </ul>",
                "    </details>",
            ])
    else:
        parts.append("    <p>No engine data available.</p>")
    parts.append("  </section>")

    # Hotspots tab
    parts.append("  <section class=\"tab-pane\" data-tab-pane=\"hotspots\">")
    parts.append("    <h2>Hotspots</h2>")
    if top_rules:
        parts.extend(
            [
                "    <section>",
                "      <h3>Common Diagnostic Rules</h3>",
                "      <table>",
                "        <thead><tr><th>Rule</th><th>Count</th></tr></thead><tbody>",
            ]
        )
        for rule, count in top_rules.items():
            parts.append(f"          <tr><td><code>{h(rule)}</code></td><td>{count}</td></tr>")
        parts.extend(["        </tbody>", "      </table>", "    </section>"])
    else:
        parts.append("    <p>No diagnostic rules recorded.</p>")

    parts.extend(
        [
            "    <section>",
            "      <h3>Top Folder Hotspots</h3>",
            "      <table>",
            "        <thead><tr><th>Folder</th><th>Errors</th><th>Warnings</th><th>Information</th><th>Runs</th></tr></thead><tbody>",
        ]
    )
    if top_folders:
        for folder in top_folders:
            parts.append(
                f"          <tr><td>{h(folder['path'])}</td><td>{folder['errors']}</td><td>{folder['warnings']}</td><td>{folder['information']}</td><td>{folder['participatingRuns']}</td></tr>"
            )
    else:
        parts.append("          <tr><td colspan=\"5\"><em>No folder hotspots</em></td></tr>")
    parts.extend(["        </tbody>", "      </table>", "    </section>"])

    parts.extend(
        [
            "    <section>",
            "      <h3>Top File Hotspots</h3>",
            "      <table>",
            "        <thead><tr><th>File</th><th>Errors</th><th>Warnings</th></tr></thead><tbody>",
        ]
    )
    if top_files:
        for file_entry in top_files:
            parts.append(
                f"          <tr><td>{h(file_entry['path'])}</td><td>{file_entry['errors']}</td><td>{file_entry['warnings']}</td></tr>"
            )
    else:
        parts.append("          <tr><td colspan=\"3\"><em>No file hotspots</em></td></tr>")
    parts.extend(["        </tbody>", "      </table>", "    </section>"])
    parts.append("  </section>")

    # Readiness tab
    parts.append("  <section class=\"tab-pane\" data-tab-pane=\"readiness\">")
    parts.append("    <h2>Strict Typing Readiness</h2>")
    strict = readiness.get("strict", {})
    ready_list = strict.get("ready", [])
    close_list = strict.get("close", [])
    blocked_list = strict.get("blocked", [])
    parts.extend(
        [
            "    <div class=\"metrics\">",
            f"      <div class=\"metric\"><strong>{len(ready_list)}</strong>Ready</div>",
            f"      <div class=\"metric\"><strong>{len(close_list)}</strong>Close</div>",
            f"      <div class=\"metric\"><strong>{len(blocked_list)}</strong>Blocked</div>",
            "    </div>",
        ]
    )

    def _render_strict_entries(label: str, entries: list[dict[str, Any]]) -> None:
        if not entries:
            parts.append(f"    <p><strong>{label}:</strong> none</p>")
            return
        parts.append(f"    <details open><summary><strong>{label}</strong> ({len(entries)})</summary>")
        parts.append("      <ul>")
        for entry in entries[:12]:
            notes = entry.get("notes") or entry.get("recommendations") or []
            note_text = f" — {', '.join(notes)}" if notes else ""
            parts.append(
                f"        <li><code>{h(entry['path'])}</code> (diagnostics={entry['diagnostics']}){note_text}</li>"
            )
        if len(entries) > 12:
            parts.append(f"        <li>… plus {len(entries) - 12} more</li>")
        parts.append("      </ul>")
        parts.append("    </details>")

    _render_strict_entries("Strict-ready folders", ready_list)
    _render_strict_entries("Close to strict", close_list)
    _render_strict_entries("Blocked", blocked_list)

    options = readiness.get("options", {})
    if options:
        parts.append("    <section>")
        parts.append("      <h3>Per-option readiness</h3>")
        parts.append(
            "      <table><thead><tr><th>Option</th><th>Ready</th><th>Close</th><th>Blocked</th><th>Close threshold</th></tr></thead><tbody>"
        )
        for category, buckets in options.items():
            label = CATEGORY_LABELS.get(category, category)
            parts.append(
                "        <tr>"
                f"<td>{h(label)}</td>"
                f"<td>{len(buckets.get('ready', []))}</td>"
                f"<td>{len(buckets.get('close', []))}</td>"
                f"<td>{len(buckets.get('blocked', []))}</td>"
                f"<td>{buckets.get('threshold', 0)}</td>"
                "</tr>"
            )
        parts.extend(["      </tbody></table>", "    </section>"])
    else:
        parts.append("    <p>No readiness data available.</p>")
    parts.append("  </section>")

    # Runs tab
    parts.append("  <section class=\"tab-pane\" data-tab-pane=\"runs\">")
    parts.append("    <h2>Run Logs</h2>")
    runs_tab = tabs.get("runs", {})
    run_details = runs_tab.get("runSummary", run_summary)
    if run_details:
        for key, data in run_details.items():
            breakdown = data.get("severityBreakdown", {})
            cmd = " ".join(h(str(part)) for part in data.get("command", []))
            parts.extend(
                [
                    "    <details class=\"run-log\" open>",
                    f"      <summary><strong>{h(key)}</strong> · command: <code>{cmd}</code></summary>",
                    "      <ul>",
                    f"        <li>Errors: {data.get('errors', 0)}</li>",
                    f"        <li>Warnings: {data.get('warnings', 0)}</li>",
                    f"        <li>Information: {data.get('information', 0)}</li>",
                    f"        <li>Total diagnostics: {data.get('total', 0)}</li>",
                    f"        <li>Severity breakdown: {breakdown if breakdown else {}}</li>",
                    "      </ul>",
                    "    </details>",
                ]
            )
    else:
        parts.append("    <p>No runs recorded.</p>")
    parts.append("  </section>")

    parts.extend(
        [
            "  <script>\n    (function(){\n      const body=document.body;\n      body.classList.remove('no-js');\n      body.classList.add('has-js');\n      const storageKey='typewiz-dashboard-tab';\n      const tabs=Array.from(document.querySelectorAll('[data-tab-target]'));\n      const panes=Array.from(document.querySelectorAll('[data-tab-pane]'));\n      function activate(name){\n        tabs.forEach(btn=>{const active=btn.dataset.tabTarget===name;btn.classList.toggle('active',active);btn.setAttribute('aria-selected',String(active));});\n        panes.forEach(pane=>pane.classList.toggle('active',pane.dataset.tabPane===name));\n      }\n      let stored=null;\n      try{stored=window.localStorage.getItem(storageKey);}catch(_){}\n      const initial=tabs.some(btn=>btn.dataset.tabTarget===stored) ? stored : body.dataset.defaultTab || 'overview';\n      activate(initial);\n      tabs.forEach(btn=>btn.addEventListener('click',()=>{const name=btn.dataset.tabTarget;activate(name);try{window.localStorage.setItem(storageKey,name);}catch(_){};}));\n    })();\n  </script>",
            "</body>",
            "</html>",
        ]
    )

    return "\n".join(parts)
