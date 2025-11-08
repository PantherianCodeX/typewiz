# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Path normalisation utilities shared by audit orchestration logic."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from typewiz.core.type_aliases import RelPath
from typewiz.runtime import ROOT_MARKERS

if TYPE_CHECKING:
    from collections.abc import Sequence


def _as_relative_path(project_root: Path, path: Path) -> RelPath:
    root = project_root.resolve()
    target = path.resolve()
    rel = os.path.relpath(str(target), str(root))
    return RelPath(Path(rel).as_posix())


def normalise_paths(project_root: Path, raw_paths: Sequence[str]) -> list[RelPath]:
    """Return unique, POSIX-style paths relative to ``project_root``."""

    normalised: list[RelPath] = []
    seen: set[str] = set()
    root = project_root.resolve()
    for raw in raw_paths:
        if not raw:
            continue
        candidate = Path(raw)
        absolute = candidate if candidate.is_absolute() else (root / candidate)
        relative = _as_relative_path(root, absolute)
        if relative not in seen:
            seen.add(relative)
            normalised.append(relative)
    return normalised


def global_fingerprint_paths(project_root: Path) -> list[RelPath]:
    """Return repository-level files that should influence fingerprinting."""

    extras: list[str] = []
    for filename in ROOT_MARKERS:
        candidate = project_root / filename
        if candidate.exists():
            extras.append(filename)
    return normalise_paths(project_root, extras)


def fingerprint_targets(
    project_root: Path,
    mode_paths: Sequence[str],
    default_paths: Sequence[str],
    extra: Sequence[str] | None = None,
) -> list[RelPath]:
    """Combine audit paths with fingerprint metadata inputs."""

    candidates = list(mode_paths) if mode_paths else list(default_paths)
    candidates.extend(global_fingerprint_paths(project_root))
    if extra:
        candidates.extend(extra)
    if not candidates:
        candidates = ["."]
    seen: set[str] = set()
    ordered: list[RelPath] = []
    for entry in candidates:
        rel_entry = RelPath(Path(entry).as_posix())
        if rel_entry not in seen:
            seen.add(rel_entry)
            ordered.append(rel_entry)
    return ordered


def normalise_override_entries(
    project_root: Path,
    override_path: Path,
    entries: Sequence[str],
) -> list[RelPath]:
    """Normalise include/exclude lists when sourced from a path override."""

    if not entries:
        entries = ["."]
    normalised: list[RelPath] = []
    seen: set[str] = set()
    for entry in entries:
        candidate = Path(entry)
        if not candidate.is_absolute():
            candidate = (override_path / candidate).resolve()
        relative = _as_relative_path(project_root, candidate)
        if relative not in seen:
            seen.add(relative)
            normalised.append(relative)
    return normalised


def relative_override_path(project_root: Path, override_path: Path) -> RelPath:
    """Resolve a path override relative to the project root if possible."""

    return _as_relative_path(project_root, override_path)
