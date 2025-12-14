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

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from ratchetr.paths import EnvOverrides, OutputFormat

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = pytest.mark.unit


def test_output_format_from_str_validates() -> None:
    assert OutputFormat.from_str("JSON") is OutputFormat.JSON
    with pytest.raises(ValueError, match="Unknown output format"):
        OutputFormat.from_str("yaml")


def test_env_overrides_from_environ_derives_cache_and_active_overrides(tmp_path: Path) -> None:
    env_home = tmp_path / "env_home"
    environ = {
        "RATCHETR_DIR": str(env_home),
        "RATCHETR_CONFIG": str(tmp_path / "config.toml"),
        "RATCHETR_ROOT": str(tmp_path),
        "RATCHETR_MANIFEST": str(tmp_path / "manifest.json"),
        "RATCHETR_CACHE_DIR": "",  # intentionally blank
    }

    overrides = EnvOverrides.from_environ(environ)

    assert overrides.cache_dir == env_home / ".cache"
    assert overrides.log_dir == env_home / "logs"
    assert overrides.active_overrides == {
        "RATCHETR_CONFIG": (tmp_path / "config.toml").resolve(),
        "RATCHETR_ROOT": tmp_path.resolve(),
        "RATCHETR_DIR": env_home.resolve(),
        "RATCHETR_MANIFEST": (tmp_path / "manifest.json").resolve(),
        "RATCHETR_LOG_DIR": (env_home / "logs").resolve(),
        "RATCHETR_CACHE_DIR": (env_home / ".cache").resolve(),
    }


def test_env_overrides_parses_include_paths_comma_separated() -> None:
    environ = {"RATCHETR_INCLUDE_PATHS": "src,tests,lib"}
    overrides = EnvOverrides.from_environ(environ)
    assert overrides.include_paths == ["src", "tests", "lib"]


def test_env_overrides_parses_include_paths_colon_separated() -> None:
    environ = {"RATCHETR_INCLUDE_PATHS": "src:tests:lib"}
    overrides = EnvOverrides.from_environ(environ)
    assert overrides.include_paths == ["src", "tests", "lib"]


def test_env_overrides_handles_empty_include_paths() -> None:
    environ = {"RATCHETR_INCLUDE_PATHS": ""}
    overrides = EnvOverrides.from_environ(environ)
    assert overrides.include_paths is None


def test_env_overrides_handles_missing_include_paths() -> None:
    environ = {}
    overrides = EnvOverrides.from_environ(environ)
    assert overrides.include_paths is None
