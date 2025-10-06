from __future__ import annotations

from html import escape
from typing import Any


def render_html(summary: dict[str, Any]) -> str:
    def h(text: str) -> str:
        return escape(text, quote=True)

    top_rules = summary.get("topRules", {})
    top_folders = summary.get("topFolders", [])
    top_files = summary.get("topFiles", [])
    severity = summary.get("severityTotals", {})

    parts: list[str] = [
        "<!DOCTYPE html>",
        "<html lang=\"en\">",
        "<head>",
        "  <meta charset=\"utf-8\" />",
        "  <title>Typing Inspector Dashboard</title>",
        "  <style>\n    body{font-family:system-ui, sans-serif;margin:2rem;background:#f5f5f5;}\n    h1,h2{color:#2b4b80;}\n    table{border-collapse:collapse;width:100%;margin-bottom:1.5rem;background:white;}\n    th,td{border:1px solid #d0d7e2;padding:0.5rem;text-align:left;}\n    th{background:#e8edf7;}\n    section{margin-bottom:2rem;}\n    .metrics{display:flex;gap:1.5rem;}\n    .metric{background:white;border:1px solid #d0d7e2;padding:1rem;border-radius:6px;min-width:8rem;text-align:center;}\n    .metric strong{display:block;font-size:1.5rem;}\n  </style>",
        "</head>",
        "<body>",
        "  <h1>Typing Inspector Dashboard</h1>",
        f"  <p><strong>Generated:</strong> {h(str(summary.get('generatedAt', 'unknown')))}<br />",
        f"     <strong>Project root:</strong> {h(str(summary.get('projectRoot', '')))}</p>",
        "  <section>",
        "    <h2>Severity Totals</h2>",
        "    <div class=\"metrics\">",
        f"      <div class=\"metric\"><strong>{severity.get('error', 0)}</strong>Errors</div>",
        f"      <div class=\"metric\"><strong>{severity.get('warning', 0)}</strong>Warnings</div>",
        f"      <div class=\"metric\"><strong>{severity.get('information', 0)}</strong>Information</div>",
        "    </div>",
        "  </section>",
        "  <section>",
        "    <h2>Run Summary</h2>",
        "    <table>",
        "      <thead><tr><th>Run</th><th>Errors</th><th>Warnings</th><th>Information</th><th>Total</th><th>Command</th></tr></thead>",
        "      <tbody>",
    ]
    for key, data in summary.get("runSummary", {}).items():
        cmd = " ".join(h(str(part)) for part in data.get("command", []))
        parts.append(
            "        <tr>"
            f"<td>{h(key)}</td>"
            f"<td>{data.get('errors', 0)}</td>"
            f"<td>{data.get('warnings', 0)}</td>"
            f"<td>{data.get('information', 0)}</td>"
            f"<td>{data.get('total', 0)}</td>"
            f"<td><code>{cmd}</code></td>"
            "</tr>"
        )
    parts.extend(
        [
            "      </tbody>",
            "    </table>",
            "  </section>",
        ]
    )

    if top_rules:
        parts.extend(
            [
                "  <section>",
                "    <h2>Top Diagnostic Rules</h2>",
                "    <table>",
                "      <thead><tr><th>Rule</th><th>Count</th></tr></thead><tbody>",
            ]
        )
        for rule, count in top_rules.items():
            parts.append(f"        <tr><td><code>{h(rule)}</code></td><td>{count}</td></tr>")
        parts.extend(["      </tbody>", "    </table>", "  </section>"])

    if top_folders:
        parts.extend(
            [
                "  <section>",
                "    <h2>Top Folder Hotspots</h2>",
                "    <table>",
                "      <thead><tr><th>Folder</th><th>Errors</th><th>Warnings</th><th>Information</th><th>Runs</th></tr></thead><tbody>",
            ]
        )
        for folder in top_folders:
            parts.append(
                f"        <tr><td>{h(folder['path'])}</td><td>{folder['errors']}</td><td>{folder['warnings']}</td><td>{folder['information']}</td><td>{folder['participatingRuns']}</td></tr>"
            )
        parts.extend(["      </tbody>", "    </table>", "  </section>"])

    if top_files:
        parts.extend(
            [
                "  <section>",
                "    <h2>Top File Hotspots</h2>",
                "    <table>",
                "      <thead><tr><th>File</th><th>Errors</th><th>Warnings</th></tr></thead><tbody>",
            ]
        )
        for file_entry in top_files:
            parts.append(
                f"        <tr><td>{h(file_entry['path'])}</td><td>{file_entry['errors']}</td><td>{file_entry['warnings']}</td></tr>"
            )
        parts.extend(["      </tbody>", "    </table>", "  </section>"])

    parts.extend(["</body>", "</html>"])
    return "\n".join(parts)
