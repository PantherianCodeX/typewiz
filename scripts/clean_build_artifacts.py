# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Utility script for deleting build artefacts during local development."""

from __future__ import annotations

import pathlib
import shutil


def main() -> int:
    """Delete common build outputs from the repository root.

    Returns:
        ``0`` once ``build/``, ``dist/``, and ``*.egg-info`` directories have
        been removed.
    """
    for name in ("build", "dist"):
        shutil.rmtree(name, ignore_errors=True)
    for egg in pathlib.Path().glob("*.egg-info"):
        shutil.rmtree(egg, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
