from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Mapping, List, Sequence, cast

from typing import cast

from .typed_manifest import ManifestData
from .readiness import compute_readiness, CATEGORY_LABELS, ReadinessEntry


def load_manifest(path: Path) -> ManifestData:
    return cast(ManifestData, json.loads(path.read_text(encoding="utf-8")))


def _collect_readiness(folder_entries: Sequence[ReadinessEntry]) -> dict[str, Any]:
    return compute_readiness(folder_entries)


def build_summary(manifest: Mapping[str, Any]) -> dict[str, Any]:
    runs = manifest.get("runs", [])
    run_summary: dict[str, Any] = {}
    folder_totals: dict[str, Counter[str]] = defaultdict(Counter)
    folder_counts: dict[str, int] = defaultdict(int)
    folder_code_totals: dict[str, Counter[str]] = defaultdict(Counter)
    folder_recommendations: dict[str, set[str]] = defaultdict(set)
    file_entries: list[tuple[str, int, int]] = []
    severity_totals: Counter[str] = Counter()
    rule_totals: Counter[str] = Counter()
    category_totals: Counter[str] = Counter()
    folder_category_totals: dict[str, Counter[str]] = defaultdict(Counter)

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
            "categoryCounts": summary.get("categoryCounts", {}),
            "engineOptions": {
                "profile": options.get("profile"),
                "configFile": options.get("configFile"),
                "pluginArgs": list(options.get("pluginArgs", [])),
                "include": list(options.get("include", [])),
                "exclude": list(options.get("exclude", [])),
                "overrides": [dict(item) for item in options.get("overrides", [])],
                "categoryMapping": dict(options.get("categoryMapping", {})),
            },
        }
        severity_totals.update(summary.get("severityBreakdown", {}))
        rule_totals.update(summary.get("ruleCounts", {}))
        category_totals.update(summary.get("categoryCounts", {}))
        for folder in run.get("perFolder", []):
            path = folder.get("path")
            if not path:
                continue
            folder_totals[path]["errors"] += folder.get("errors", 0)
            folder_totals[path]["warnings"] += folder.get("warnings", 0)
            folder_totals[path]["information"] += folder.get("information", 0)
            folder_counts[path] += 1
            for code, count in folder.get("codeCounts", {}).items():
                folder_code_totals[path][code] += count
            for category, count in folder.get("categoryCounts", {}).items():
                folder_category_totals[path][category] += count
            for rec in folder.get("recommendations", []):
                folder_recommendations[path].add(rec)
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

    folder_entries_full: List[ReadinessEntry] = []
    for path, counts in folder_totals.items():
        folder_entries_full.append(
            {
                "path": path,
                "errors": counts["errors"],
                "warnings": counts["warnings"],
                "information": counts["information"],
                "codeCounts": dict(folder_code_totals.get(path, {})),
                "categoryCounts": dict(folder_category_totals.get(path, {})),
                "recommendations": sorted(folder_recommendations.get(path, [])),
            }
        )

    top_folders = sorted(
        folder_totals.items(),
        key=lambda item: (-item[1]["errors"], -item[1]["warnings"], item[0]),
    )[:25]
    top_files = sorted(
        file_entries,
        key=lambda item: (-item[1], -item[2], item[0]),
    )[:25]
    readiness = _collect_readiness(cast(Sequence[ReadinessEntry], folder_entries_full))

    top_rules_dict = dict(rule_totals.most_common(20))
    folder_entry_lookup: Dict[str, ReadinessEntry] = {entry["path"]: entry for entry in folder_entries_full}
    top_folders_list = []
    for path, counts in top_folders:
        entry = folder_entry_lookup.get(path, {})
        top_folders_list.append(
            {
                "path": path,
                "errors": counts["errors"],
                "warnings": counts["warnings"],
                "information": counts["information"],
                "participatingRuns": folder_counts[path],
                "codeCounts": entry.get("codeCounts", {}),
                "recommendations": entry.get("recommendations", []),
            }
        )
    top_files_list = [
        {"path": path, "errors": errors, "warnings": warnings} for path, errors, warnings in top_files
    ]

    return {
        "generatedAt": manifest.get("generatedAt"),
        "projectRoot": manifest.get("projectRoot"),
        "runSummary": run_summary,
        "severityTotals": dict(severity_totals),
        "categoryTotals": dict(category_totals),
        "topRules": top_rules_dict,
        "topFolders": top_folders_list,
        "topFiles": top_files_list,
        "tabs": {
            "overview": {
                "severityTotals": dict(severity_totals),
                "categoryTotals": dict(category_totals),
                "runSummary": run_summary,
            },
            "engines": {
                "runSummary": run_summary,
            },
            "hotspots": {
                "topRules": top_rules_dict,
                "topFolders": top_folders_list,
                "topFiles": top_files_list,
            },
            "readiness": readiness,
            "runs": {
                "runSummary": run_summary,
            },
        },
    }


def render_markdown(summary: dict[str, Any]) -> str:
    tabs = summary.get("tabs", {})
    overview = tabs.get("overview", {})
    run_summary = overview.get("runSummary", summary.get("runSummary", {}))
    severity = overview.get("severityTotals", summary.get("severityTotals", {}))
    hotspots = tabs.get("hotspots", {})

    lines: list[str] = [
        "# typewiz Dashboard",
        "",
        f"- Generated at: {summary.get('generatedAt')}",
        f"- Project root: `{summary.get('projectRoot')}`",
    ]

    if severity:
        lines.extend(
            [
                "",
                "## Overview",
                "",
                f"- Errors: {severity.get('error', 0)}",
                f"- Warnings: {severity.get('warning', 0)}",
                f"- Information: {severity.get('information', 0)}",
            ]
        )

    lines.extend(
        [
            "",
            "### Run summary",
            "",
            "| Run | Errors | Warnings | Information | Command |",
            "| --- | ---: | ---: | ---: | --- |",
        ]
    )
    for key, data in run_summary.items():
        cmd = " ".join(str(part) for part in data.get("command", []))
        lines.append(
            f"| `{key}` | {data.get('errors', 0)} | {data.get('warnings', 0)} | {data.get('information', 0)} | `{cmd}` |"
        )
    if not run_summary:
        lines.append("| _No runs recorded_ | 0 | 0 | 0 | — |")

    lines.extend(["", "### Engine details"])
    if run_summary:
        for key, data in run_summary.items():
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
    else:
        lines.append("- No engine data available")

    lines.extend(["", "### Hotspots"])
    top_rules = hotspots.get("topRules", summary.get("topRules", {}))
    if top_rules:
        lines.extend(
            [
                "",
                "#### Diagnostic rules",
                "",
                "| Rule | Count |",
                "| --- | ---: |",
            ]
        )
        for rule, count in top_rules.items():
            lines.append(f"| `{rule}` | {count} |")
    else:
        lines.append("- No diagnostic rules recorded")

    top_folders = hotspots.get("topFolders", summary.get("topFolders", []))
    lines.extend(
        [
            "",
            "#### Folder hotspots",
            "",
            "| Folder | Errors | Warnings | Information | Runs |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    if top_folders:
        for folder in top_folders:
            lines.append(
                f"| `{folder['path']}` | {folder['errors']} | {folder['warnings']} | {folder['information']} | {folder['participatingRuns']} |"
            )
    else:
        lines.append("| _No folder hotspots_ | 0 | 0 | 0 | 0 |")

    top_files = hotspots.get("topFiles", summary.get("topFiles", []))
    lines.extend(
        [
            "",
            "#### File hotspots",
            "",
            "| File | Errors | Warnings |",
            "| --- | ---: | ---: |",
        ]
    )
    if top_files:
        for file_entry in top_files:
            lines.append(f"| `{file_entry['path']}` | {file_entry['errors']} | {file_entry['warnings']} |")
    else:
        lines.append("| _No file hotspots_ | 0 | 0 |")

    lines.extend(["", "### Run logs"])
    readiness_tab = tabs.get("readiness", {})
    runs_tab = tabs.get("runs", {})
    run_details = runs_tab.get("runSummary", run_summary)
    if run_details:
        for key, data in run_details.items():
            breakdown = data.get("severityBreakdown", {})
            lines.extend(
                [
                    "",
                    f"#### `{key}`",
                    f"- Errors: {data.get('errors', 0)}",
                    f"- Warnings: {data.get('warnings', 0)}",
                    f"- Information: {data.get('information', 0)}",
                    f"- Total diagnostics: {data.get('total', 0)}",
                    f"- Severity breakdown: {breakdown if breakdown else '{}'}",
                ]
            )
    else:
        lines.append("- No runs recorded")

    lines.extend(["", "### Readiness snapshot"])
    strict = readiness_tab.get("strict", {})

    def _format_entry_list(entries: list[dict[str, Any]], limit: int = 8) -> str:
        if not entries:
            return "—"
        paths = [f"`{entry['path']}`" for entry in entries[:limit]]
        if len(entries) > limit:
            paths.append(f"… +{len(entries) - limit} more")
        return ", ".join(paths)

    lines.append(
        f"- Ready for strict typing: {_format_entry_list(strict.get('ready', []))}"
    )
    lines.append(
        f"- Close to strict typing: {_format_entry_list(strict.get('close', []))}"
    )
    lines.append(
        f"- Blocked folders: {_format_entry_list(strict.get('blocked', []))}"
    )

    options = readiness_tab.get("options", {})
    if options:
        lines.extend(["", "#### Per-option readiness"])
        for category, buckets in options.items():
            label = CATEGORY_LABELS.get(category, category)
            lines.append(f"- **{label}** (≤{buckets.get('threshold', 0)} to be close):")
            for status in ("ready", "close", "blocked"):
                entries = buckets.get(status, [])
                lines.append(
                    f"  - {status.title()}: {_format_entry_list(entries)}"
                )

    lines.append("")
    return "\n".join(lines)
