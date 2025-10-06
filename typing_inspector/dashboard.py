from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    runs = manifest.get("runs", [])
    run_summary: dict[str, Any] = {}
    folder_totals: dict[str, Counter[str]] = defaultdict(Counter)
    folder_counts: dict[str, int] = defaultdict(int)
    file_entries: list[tuple[str, int, int]] = []

    for run in runs:
        key = f"{run.get('tool')}:{run.get('mode')}"
        summary = run.get("summary", {})
        run_summary[key] = {
            "command": run.get("command"),
            "errors": summary.get("errors", 0),
            "warnings": summary.get("warnings", 0),
            "information": summary.get("information", 0),
            "total": summary.get("total", 0),
        }
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
        "runSummary": run_summary,
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
            {"path": path, "errors": errors, "warnings": warnings} for path, errors, warnings in top_files
        ],
    }


def render_markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"# Typing Inspector Dashboard",
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

    lines.append("")
    return "\n".join(lines)

