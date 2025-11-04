from __future__ import annotations

from collections.abc import Sequence

from .collection_utils import dedupe_preserve
from .model_types import OverrideEntry


def get_override_components(
    entry: OverrideEntry,
) -> tuple[str, str | None, list[str], list[str], list[str]]:
    path = entry.get("path", "—") or "—"
    profile = entry.get("profile")
    plugin_args = dedupe_preserve(entry.get("pluginArgs", []))
    include_paths = dedupe_preserve(entry.get("include", []))
    exclude_paths = dedupe_preserve(entry.get("exclude", []))
    return path, profile, plugin_args, include_paths, exclude_paths


def format_override_inline(entry: OverrideEntry) -> str:
    path, profile, plugin_args, include_paths, exclude_paths = get_override_components(entry)
    details: list[str] = []
    if profile:
        details.append(f"profile={profile}")
    if plugin_args:
        details.append("args=" + "/".join(plugin_args))
    if include_paths:
        details.append("include=" + "/".join(include_paths))
    if exclude_paths:
        details.append("exclude=" + "/".join(exclude_paths))
    if details:
        return f"{path}({', '.join(details)})"
    return path


def format_overrides_block(entries: Sequence[OverrideEntry]) -> list[str]:
    lines: list[str] = []
    for entry in entries:
        path, profile, plugin_args, include_paths, exclude_paths = get_override_components(entry)
        details: list[str] = []
        if profile:
            details.append(f"profile={profile}")
        if plugin_args:
            formatted_args = ", ".join(f"`{arg}`" for arg in plugin_args)
            details.append(f"plugin args: {formatted_args}")
        if include_paths:
            formatted_inc = ", ".join(f"`{item}`" for item in include_paths)
            details.append(f"include: {formatted_inc}")
        if exclude_paths:
            formatted_exc = ", ".join(f"`{item}`" for item in exclude_paths)
            details.append(f"exclude: {formatted_exc}")
        if not details:
            details.append("no explicit changes")
        lines.append(f"  - `{path}` ({'; '.join(details)})")
    return lines


def override_detail_lines(entry: OverrideEntry) -> tuple[str, list[str]]:
    path, profile, plugin_args, include_paths, exclude_paths = get_override_components(entry)
    details: list[str] = []
    if profile:
        details.append(f"profile={profile}")
    if plugin_args:
        details.append("plugin args=" + ", ".join(plugin_args))
    if include_paths:
        details.append("include=" + ", ".join(include_paths))
    if exclude_paths:
        details.append("exclude=" + ", ".join(exclude_paths))
    if not details:
        details.append("no explicit changes")
    return path, details
