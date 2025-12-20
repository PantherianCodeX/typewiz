#!/usr/bin/env python3
"""Generate s11r2 progress outputs.

Thin wrapper around the implementation in `scripts/docs/s11r2_progress/`.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Final


_REPO_ROOT_PARENT_LEVELS: Final[int] = 2


def main(argv: list[str]) -> int:
    """Entry point."""

    repo_root = Path(__file__).resolve().parents[_REPO_ROOT_PARENT_LEVELS]
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)

    from scripts.docs.s11r2_progress import main as _main

    return _main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
