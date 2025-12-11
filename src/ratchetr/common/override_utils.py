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

"""Formatting helpers for path override payloads."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ratchetr.collections import dedupe_preserve

if TYPE_CHECKING:
    from collections.abc import Sequence

    from ratchetr.core.model_types import OverrideEntry
    from ratchetr.core.type_aliases import RelPath


def get_override_components(
    entry: OverrideEntry,
) -> tuple[str, str | None, list[str], list[RelPath], list[RelPath]]:
    """Return normalised override components for consistent rendering.

    Args:
        entry: Override mapping pulled from manifest data.

    Returns:
        Tuple of path, profile, plugin args, include paths, and exclude paths.
    """
    path = entry.get("path", "—") or "—"
    profile = entry.get("profile")
    plugin_args = dedupe_preserve(entry.get("pluginArgs", []))
    include_paths = dedupe_preserve(entry.get("include", []))
    exclude_paths = dedupe_preserve(entry.get("exclude", []))
    return path, profile, plugin_args, include_paths, exclude_paths


def format_override_inline(entry: OverrideEntry) -> str:
    """Render an override entry as a compact inline description.

    Args:
        entry: Override entry to render.

    Returns:
        String representation summarising the override.
    """
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
    """Render override entries as Markdown bullet lines.

    Args:
        entries: Sequence of overrides to include in the block.

    Returns:
        List of Markdown lines detailing each override.
    """
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
    """Return a ``(path, details)`` tuple for detailed override reporting.

    Args:
        entry: Override entry to normalise.

    Returns:
        Tuple containing the override path and a list of detail strings.
    """
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


__all__ = [
    "format_override_inline",
    "format_overrides_block",
    "get_override_components",
    "override_detail_lines",
]
