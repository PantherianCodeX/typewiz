# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

pytest_plugins = ("tests.fixtures.snapshots",)
