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

"""Utility script for deleting build artefacts during local development."""

from __future__ import annotations

import pathlib
import shutil


def main() -> int:
    """Delete common build outputs from the repository root.

    Returns:
        `0`once ``build/``, ``dist/``, and `*.egg-info`directories have
        been removed.
    """
    for name in ("build", "dist"):
        shutil.rmtree(name, ignore_errors=True)
    for egg in pathlib.Path().glob("*.egg-info"):
        shutil.rmtree(egg, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
