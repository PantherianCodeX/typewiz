# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""PEP 338 entrypoint for ``python -m typewiz``."""

from __future__ import annotations

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
