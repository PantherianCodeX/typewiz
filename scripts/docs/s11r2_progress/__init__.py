"""s11r2 progress roll-up + dashboard generator (library).

The CLI entrypoint is `scripts/docs/s11r2-progress.py`.

This package is intentionally small and self-contained so it can be executed in
minimal environments while still remaining strongly typed and lint-friendly.
"""

from __future__ import annotations

from scripts.docs.s11r2_progress.cli import main

__all__ = ["main"]
