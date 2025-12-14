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

"""Integration tests for configuration discovery and repo root detection."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ratchetr.config import load_config

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.integration


def test_load_config_discovers_repo_root_from_subdirectory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path / "project"
    repo_root.mkdir()
    config_path = repo_root / "ratchetr.toml"
    config_path.write_text(
        """
[audit]
include_paths = ["root-discovery"]
""",
        encoding="utf-8",
    )
    nested = repo_root / "apps" / "pkg"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)

    cfg = load_config()

    assert cfg.audit.include_paths == ["root-discovery"]
