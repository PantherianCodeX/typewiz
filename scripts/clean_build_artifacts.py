# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

import pathlib
import shutil


def main() -> int:
    for name in ("build", "dist"):
        shutil.rmtree(name, ignore_errors=True)
    for egg in pathlib.Path().glob("*.egg-info"):
        shutil.rmtree(egg, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
