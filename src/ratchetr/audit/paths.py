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

"""Path normalisation utilities shared by audit orchestration logic."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from ratchetr.core.type_aliases import RelPath
from ratchetr.runtime import ROOT_MARKERS

if TYPE_CHECKING:
    from collections.abc import Sequence


def _as_relative_path(project_root: Path, path: Path) -> RelPath:
    root = project_root.resolve()
    target = path.resolve()
    rel = os.path.relpath(str(target), str(root))
    return RelPath(Path(rel).as_posix())


def normalise_paths(project_root: Path, raw_paths: Sequence[str]) -> list[RelPath]:
    """Return unique, POSIX-style paths relative to ``project_root``.

    Args:
        project_root: Root directory used to resolve relative paths.
        raw_paths: Raw path strings provided by the user or configuration.

    Returns:
        Deduplicated list of relative paths in POSIX format.
    """
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


def canonicalize_scope(project_root: Path, raw_paths: Sequence[str]) -> list[RelPath]:
    """Return canonicalized scope: deduplicated, normalized, and sorted.

    This function produces a deterministic scope representation suitable for
    equivalence comparisons in EnginePlan. Order-invariant equality requires
    consistent sorting.

    Args:
        project_root: Root directory used to resolve relative paths.
        raw_paths: Raw path strings provided by the user or configuration.

    Returns:
        Sorted, deduplicated list of relative paths in POSIX format.
    """
    normalized = normalise_paths(project_root, raw_paths)
    return sorted(normalized)


def global_fingerprint_paths(project_root: Path) -> list[RelPath]:
    """Return repository-level files that should influence fingerprinting.

    Args:
        project_root: Repository root used to locate marker files.

    Returns:
        Relative paths to any root marker files that exist.
    """
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
    """Combine audit paths with fingerprint metadata inputs.

    Args:
        project_root: Repository root used to derive relative paths for
            fingerprint hashing.
        mode_paths: Paths requested for the current run mode.
        default_paths: Baseline paths from the audit configuration.
        extra: Optional additional fingerprint entries (e.g. config fragments).

    Returns:
        Ordered, deduplicated relative paths whose contents influence cache
        fingerprints.
    """
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
    """Normalise include/exclude lists when sourced from a path override.

    Args:
        project_root: Repository root for relative path computation.
        override_path: Directory containing the override configuration file.
        entries: Include/exclude strings supplied within the override.

    Returns:
        Deduplicated relative paths rooted at ``project_root``.
    """
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
    """Resolve a path override relative to the project root if possible.

    Args:
        project_root: Repository root for computing relative locations.
        override_path: Absolute path to the override file or directory.

    Returns:
        The override path expressed as a `RelPath`relative to
        ``project_root``.
    """
    return _as_relative_path(project_root, override_path)
