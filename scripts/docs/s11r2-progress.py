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

# ignore JUSTIFIED: Script filename includes a dash for CLI parity.
# pylint: disable=invalid-name  # ruff: noqa: N999

"""Generate s11r2 progress outputs.

Thin wrapper around the implementation in `scripts/docs/s11r2_progress/`.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Final

from scripts.docs.s11r2_progress import main as _main

_REPO_ROOT_PARENT_LEVELS: Final[int] = 2


def main(argv: list[str]) -> int:
    """Entry point.

    Args:
        argv: CLI arguments (excluding the executable).

    Returns:
        Exit code (0 for success).
    """
    repo_root = Path(__file__).resolve().parents[_REPO_ROOT_PARENT_LEVELS]
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)

    return _main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
