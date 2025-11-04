"""Path normalisation utilities shared by audit orchestration logic."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


def normalise_paths(project_root: Path, raw_paths: Sequence[str]) -> list[str]:
    """Return unique, POSIX-style paths relative to ``project_root`` where possible."""

    normalised: list[str] = []
    seen: set[str] = set()
    root = project_root.resolve()
    for raw in raw_paths:
        if not raw:
            continue
        candidate = Path(raw)
        absolute = candidate if candidate.is_absolute() else (root / candidate)
        absolute = absolute.resolve()
        try:
            relative = absolute.relative_to(root).as_posix()
        except ValueError:
            relative = absolute.as_posix()
        if relative not in seen:
            seen.add(relative)
            normalised.append(relative)
    return normalised


def global_fingerprint_paths(project_root: Path) -> list[str]:
    """Return repository-level files that should influence fingerprinting."""

    extras: list[str] = []
    for filename in ("typewiz.toml", ".typewiz.toml", "pyproject.toml"):
        candidate = project_root / filename
        if candidate.exists():
            extras.append(filename)
    return normalise_paths(project_root, extras)


def fingerprint_targets(
    project_root: Path,
    mode_paths: Sequence[str],
    default_paths: Sequence[str],
    extra: Sequence[str] | None = None,
) -> list[str]:
    """Combine audit paths with fingerprint metadata inputs."""

    candidates = list(mode_paths) if mode_paths else list(default_paths)
    candidates.extend(global_fingerprint_paths(project_root))
    if extra:
        candidates.extend(extra)
    if not candidates:
        candidates = ["."]
    seen: set[str] = set()
    ordered: list[str] = []
    for entry in candidates:
        if entry not in seen:
            seen.add(entry)
            ordered.append(entry)
    return ordered


def normalise_override_entries(
    project_root: Path, override_path: Path, entries: Sequence[str]
) -> list[str]:
    """Normalise include/exclude lists when sourced from a path override."""

    if not entries:
        entries = ["."]
    normalised: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        candidate = Path(entry)
        if not candidate.is_absolute():
            candidate = (override_path / candidate).resolve()
        try:
            relative = candidate.resolve().relative_to(project_root.resolve()).as_posix()
        except ValueError:
            relative = candidate.resolve().as_posix()
        if relative not in seen:
            seen.add(relative)
            normalised.append(relative)
    return normalised


def relative_override_path(project_root: Path, override_path: Path) -> str:
    """Resolve a path override relative to the project root if possible."""

    try:
        return override_path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return override_path.resolve().as_posix()
