from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Mapping

from typing import cast

from .typed_manifest import ManifestData


def load_manifest(path: Path) -> ManifestData:
    return cast(ManifestData, json.loads(path.read_text(encoding="utf-8")))


def build_summary(manifest: Mapping[str, Any]) -> dict[str, Any]:
    runs = manifest.get("runs", [])
    run_summary: dict[str, Any] = {}
    folder_totals: dict[str, Counter[str]] = defaultdict(Counter)
    folder_counts: dict[str, int] = defaultdict(int)
    file_entries: list[tuple[str, int, int]] = []
    severity_totals: Counter[str] = Counter()
    rule_totals: Counter[str] = Counter()

    for run in runs:
        key = f"{run.get('tool')}:{run.get('mode')}"
        summary = run.get("summary", {})
        options = run.get("engineOptions", {})
        run_summary[key] = {
            "command": run.get("command"),
            "errors": summary.get("errors", 0),
            "warnings": summary.get("warnings", 0),
            "information": summary.get("information", 0),
            "total": summary.get("total", 0),
            "severityBreakdown": summary.get("severityBreakdown", {}),
            "ruleCounts": summary.get("ruleCounts", {}),
            "engineOptions": {
                "profile": options.get("profile"),
                "configFile": options.get("configFile"),
                "pluginArgs": list(options.get("pluginArgs", [])),
                "include": list(options.get("include", [])),
                "exclude": list(options.get("exclude", [])),
                "overrides": [dict(item) for item in options.get("overrides", [])],
            },
        }
        severity_totals.update(summary.get("severityBreakdown", {}))
        rule_totals.update(summary.get("ruleCounts", {}))
        for folder in run.get("perFolder", []):
            path = folder.get("path")
            if not path:
                continue
            folder_totals[path]["errors"] += folder.get("errors", 0)
            folder_totals[path]["warnings"] += folder.get("warnings", 0)
            folder_totals[path]["information"] += folder.get("information", 0)
            folder_counts[path] += 1
        for entry in run.get("perFile", []):
            errors = entry.get("errors", 0)
            warnings = entry.get("warnings", 0)
            if not errors and not warnings:
                continue
            file_entries.append(
                (
                    entry.get("path", "<unknown>"),
                    errors,
                    warnings,
                )
            )

    top_folders = sorted(
        folder_totals.items(),
        key=lambda item: (-item[1]["errors"], -item[1]["warnings"], item[0]),
    )[:25]
    top_files = sorted(
        file_entries,
        key=lambda item: (-item[1], -item[2], item[0]),
    )[:25]

    return {
        "generatedAt": manifest.get("generatedAt"),
        "projectRoot": manifest.get("projectRoot"),
        "tabs": {
            "overview": {
                "severityTotals": dict(severity_totals),
                "runSummary": run_summary,
            },
            "engines": {
                "runSummary": run_summary,
            },
            "hotspots": {
                "topRules": dict(rule_totals.most_common(20)),
                "topFolders": [
                    {
                        "path": path,
                        "errors": counts["errors"],
                        "warnings": counts["warnings"],
                        "information": counts["information"],
                        "participatingRuns": folder_counts[path],
                    }
                    for path, counts in top_folders
                ],
                "topFiles": [
                    {"path": path, "errors": errors, "warnings": warnings}
                    for path, errors, warnings in top_files
                ],
            },
            "runs": {
                "runSummary": run_summary,
            },
        },
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"# typewiz Dashboard",
        "",
        f"- Generated at: {summary.get('generatedAt')}",
        f"- Project root: `{summary.get('projectRoot')}`",
        "",
        "## Run Summary",
        "",
        "| Run | Errors | Warnings | Information | Command |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for key, data in summary.get("runSummary", {}).items():
        cmd = " ".join(str(part) for part in data.get("command", []))
        lines.append(
            f"| `{key}` | {data.get('errors', 0)} | {data.get('warnings', 0)} | {data.get('information', 0)} | `{cmd}` |"
        )
    if summary.get("runSummary"):
        lines.extend(["", "### Engine Options"])
        for key, data in summary.get("runSummary", {}).items():
            options = data.get("engineOptions", {})
            profile = options.get("profile") or "—"
            config_file = options.get("configFile") or "—"
            plugin_args = ", ".join(f"`{arg}`" for arg in options.get("pluginArgs", []) or []) or "—"
            include = ", ".join(f"`{path}`" for path in options.get("include", []) or []) or "—"
            exclude = ", ".join(f"`{path}`" for path in options.get("exclude", []) or []) or "—"
            lines.extend(
                [
                    "",
                    f"#### `{key}`",
                    f"- Profile: {profile}",
                    f"- Config file: {config_file}",
                    f"- Plugin args: {plugin_args}",
                    f"- Include paths: {include}",
                    f"- Exclude paths: {exclude}",
                ]
            )
            overrides = options.get("overrides", []) or []
            if overrides:
                lines.append("- Folder overrides:")
                for override in overrides:
                    path = override.get("path", "—")
                    details: list[str] = []
                    if override.get("profile"):
                        details.append(f"profile={override['profile']}")
                    if override.get("pluginArgs"):
                        args_list = ", ".join(f"`{arg}`" for arg in override.get("pluginArgs", []))
                        details.append(f"plugin args: {args_list}")
                    if override.get("include"):
                        inc_list = ", ".join(f"`{item}`" for item in override.get("include", []))
                        details.append(f"include: {inc_list}")
                    if override.get("exclude"):
                        exc_list = ", ".join(f"`{item}`" for item in override.get("exclude", []))
                        details.append(f"exclude: {exc_list}")
                    if not details:
                        details.append("no explicit changes")
                    lines.append(f"  - `{path}` ({'; '.join(details)})")

    lines.extend(
        [
            "",
            "## Top Folder Hotspots",
            "",
            "| Folder | Errors | Warnings | Information | Runs |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for folder in summary.get("topFolders", []):
        lines.append(
            f"| `{folder['path']}` | {folder['errors']} | {folder['warnings']} | {folder['information']} | {folder['participatingRuns']} |"
        )

    lines.extend(
        [
            "",
            "## Top File Hotspots",
            "",
            "| File | Errors | Warnings |",
            "| --- | ---: | ---: |",
        ]
    )
    for file_entry in summary.get("topFiles", []):
        lines.append(f"| `{file_entry['path']}` | {file_entry['errors']} | {file_entry['warnings']} |")

    if summary.get("topRules"):
        lines.extend(
            [
                "",
                "## Most Common Diagnostic Rules",
                "",
                "| Rule | Count |",
                "| --- | ---: |",
            ]
        )
        for rule, count in summary.get("topRules", {}).items():
            lines.append(f"| `{rule}` | {count} |")

    if summary.get("severityTotals"):
        totals = summary["severityTotals"]
        lines.extend(
            [
                "",
                "## Severity Totals",
                "",
                f"- Errors: {totals.get('error', 0)}",
                f"- Warnings: {totals.get('warning', 0)}",
                f"- Information: {totals.get('information', 0)}",
            ]
        )

    lines.append("")
    return "\n".join(lines)
