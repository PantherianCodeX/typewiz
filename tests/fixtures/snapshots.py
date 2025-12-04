# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Snapshot fixtures and helpers shared across the test suite."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

__all__ = ["SnapshotMissingError", "snapshots_dir", "snapshot_text", "assert_snapshot"]


class SnapshotMissingError(AssertionError):
    """Raised when an expected snapshot fixture is missing."""

    def __init__(self, name: str, path: Path) -> None:
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
    """Load snapshot text, raising when the named snapshot cannot be found."""

    def loader(name: str) -> str:
        path = snapshots_dir / name
        if not path.exists():
            raise SnapshotMissingError(name, path)
        return path.read_text(encoding="utf-8")

    return loader


def assert_snapshot(actual: str, name: str, *, snapshots_dir: Path | None = None) -> None:
    """Compare text against the stored snapshot."""
    directory = snapshots_dir or _snapshots_root()
    expected = directory / name
    if not expected.exists():
        raise SnapshotMissingError(name, expected)
    assert actual == expected.read_text(encoding="utf-8")
