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

"""Filesystem helpers for locating project roots and scanning directories."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Final, Literal, TypeAlias, cast

from ratchetr.core.model_types import LogComponent
from ratchetr.logging import structured_extra

logger: logging.Logger = logging.getLogger("ratchetr.internal.paths")

__all__ = ["ROOT_MARKERS", "RootMarker", "default_full_paths", "resolve_project_root"]

RootMarker: TypeAlias = Literal["ratchetr.toml", ".ratchetr.toml", "pyproject.toml"]

ROOT_MARKERS: Final[tuple[RootMarker, RootMarker, RootMarker]] = (
    "ratchetr.toml",
    ".ratchetr.toml",
    "pyproject.toml",
)


def _contains_python(path: Path) -> bool:
    if not path.exists():
        return False
    if path.is_file() and path.suffix in {".py", ".pyi"}:
        return True
    if not path.is_dir():
        return False
    for child in path.iterdir():
        if child.is_file() and child.suffix in {".py", ".pyi"}:
            return True
        if child.is_dir() and _contains_python(child):
            return True
    return False


def default_full_paths(root: Path) -> list[str]:
    """Return candidate folders containing Python sources beneath a root.

    Args:
        root: Project root to scan for standard package directories.

    Returns:
        List of relative folder names to include in full runs.
    """
    candidates = ["ratchetr", "apps", "packages", "config", "infra", "tests"]
    paths: list[str] = []
    for item in candidates:
        full = root / item
        if _contains_python(full):
            paths.append(item)
    if not paths:
        paths.append(".")
    return paths


def resolve_project_root(start: Path | None = None) -> Path:
    """Resolve the project root by walking parent directories for markers.

    Args:
        start: Optional starting path (defaults to current working directory).

    Returns:
        Path to the discovered project root.

    Raises:
        FileNotFoundError: If ``start`` is provided but does not exist.
    """
    base = (start or Path.cwd()).resolve()
    if base.is_file():
        base = base.parent

    checked: list[Path] = []
    for candidate in (base, *base.parents):
        checked.append(candidate)
        for marker in ROOT_MARKERS:
            if (candidate / marker).exists():
                return candidate

    if start is not None:
        if not base.exists():
            message = f"Provided project root {start} does not exist."
            raise FileNotFoundError(message)
        logger.debug(
            "No project markers found; using provided path %s as project root",
            base,
            extra=_structured_extra(path=base),
        )
        return base

    logger.debug(
        "No project markers found in %s; using current working directory as root",
        ", ".join(str(path) for path in checked),
        extra=_structured_extra(details={"checked": [str(path) for path in checked]}),
    )
    return base


def _structured_extra(**kwargs: object) -> dict[str, object]:
    payload = structured_extra(LogComponent.SERVICES, **cast("dict[str, Any]", kwargs))
    return cast("dict[str, object]", payload)
