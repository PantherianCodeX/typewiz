# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Snapshot fixtures and helpers shared across the test suite."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["SnapshotMissingError", "assert_snapshot", "snapshot_text", "snapshots_dir"]


class SnapshotMissingError(AssertionError):
    """Raised when an expected snapshot fixture is missing."""

    def __init__(self, name: str, path: Path) -> None:
        """Initialise the error with the missing snapshot metadata."""
        self.name = name
        self.path = path
        super().__init__(f"Snapshot {name} missing at {path}")


def _snapshots_root() -> Path:
    return Path(__file__).resolve().parents[1] / "snapshots"


@pytest.fixture
def snapshots_dir() -> Path:
    """Return the root snapshot directory used by global fixtures."""
    return _snapshots_root()


@pytest.fixture
def snapshot_text(snapshots_dir: Path) -> Callable[[str], str]:
    """Load snapshot text, raising when the named snapshot cannot be found.

    Returns:
        Callable that returns the snapshot contents for a given name.

    Note:
        The returned loader raises ``SnapshotMissingError`` when files are missing.
    """

    def loader(name: str) -> str:
        path = snapshots_dir / name
        if not path.exists():
            raise SnapshotMissingError(name, path)
        return path.read_text(encoding="utf-8")

    return loader


def assert_snapshot(actual: str, name: str, *, snapshots_dir: Path | None = None) -> None:
    """Compare text against the stored snapshot.

    Args:
        actual: Newly produced text.
        name: Snapshot filename relative to ``snapshots_dir``.
        snapshots_dir: Optional override for the snapshot root.

    Raises:
        SnapshotMissingError: If the snapshot file cannot be found.
    """
    directory = snapshots_dir or _snapshots_root()
    expected = directory / name
    if not expected.exists():
        raise SnapshotMissingError(name, expected)
    assert actual == expected.read_text(encoding="utf-8")
