# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Pytest entry point that wires shared fixtures and markers."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

pytest_plugins = ("tests.fixtures.snapshots",)


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with the custom markers used by the test suite."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line(
        "markers",
        "integration: Integration tests (slower, multiple components)",
    )
    config.addinivalue_line("markers", "property: Property-based tests")
    config.addinivalue_line("markers", "benchmark: Performance benchmark tests")
    config.addinivalue_line("markers", "slow: Slow-running tests")
    config.addinivalue_line("markers", "cli: CLI-related tests")
    config.addinivalue_line("markers", "engine: Engine-related tests")
    config.addinivalue_line("markers", "ratchet: Ratchet feature tests")
