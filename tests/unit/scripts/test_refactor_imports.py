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

"""Unit tests for Misc Refactor Imports."""

from __future__ import annotations

import argparse
import importlib.util
import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

pytestmark = pytest.mark.unit

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_PATH = REPO_ROOT / "scripts" / "refactor_imports.py"
SPEC = importlib.util.spec_from_file_location("refactor_imports", MODULE_PATH)
assert SPEC
assert SPEC.loader
_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = _module
SPEC.loader.exec_module(_module)
MODULE: Any = _module

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch


def test_rewrite_content_updates_from_import() -> None:
    content = "from foo.bar import Baz\n"
    new_content, changed = MODULE.rewrite_content(content, {"foo.bar": "new.mod"})
    assert changed
    assert new_content == "from new.mod import Baz\n"


def test_relative_import_resolves_to_absolute_module() -> None:
    content = "from ..utils import helper\n"
    new_content, changed = MODULE.rewrite_content(
        content,
        {"pkg.utils": "pkg._infra.utils"},
        current_module="pkg.sub.module",
    )
    assert changed
    assert new_content == "from pkg._infra.utils import helper\n"


def test_identity_mapping_normalizes_relative_path() -> None:
    content = "from .._infra.utils import helper\n"
    new_content, changed = MODULE.rewrite_content(
        content,
        {"pkg._infra.utils": "pkg._infra.utils"},
        current_module="pkg.core.mod",
    )
    assert changed
    assert new_content == "from pkg._infra.utils import helper\n"


def test_cli_apply_updates_files(tmp_path: Path) -> None:
    target = tmp_path / "example.py"
    _ = target.write_text("import alpha.beta as ab\n", encoding="utf-8")

    exit_code = MODULE.main([
        "--root",
        str(tmp_path),
        "--map",
        "alpha.beta=core.gamma",
        "--apply",
    ])
    assert exit_code == 0
    assert target.read_text(encoding="utf-8") == "import core.gamma as ab\n"


def test_cli_dry_run_does_not_modify(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    target = tmp_path / "demo.py"
    _ = target.write_text("from foo import bar\n", encoding="utf-8")

    exit_code = MODULE.main(["--root", str(tmp_path), "--map", "foo=baz"])
    assert exit_code == 0
    assert target.read_text(encoding="utf-8") == "from foo import bar\n"
    captured = capsys.readouterr()
    assert "Would update" in captured.out


def test_mapping_file_support(tmp_path: Path) -> None:
    target = tmp_path / "pkg.py"
    _ = target.write_text("import old.module\n", encoding="utf-8")
    mapping_file = tmp_path / "mappings.txt"
    _ = mapping_file.write_text("# comment\nold.module=new.module\n", encoding="utf-8")

    exit_code = MODULE.main([
        "--root",
        str(tmp_path),
        "--mapping-file",
        str(mapping_file),
        "--apply",
    ])
    assert exit_code == 0
    assert target.read_text(encoding="utf-8") == "import new.module\n"


def test_parse_map_entries_requires_values() -> None:
    with pytest.raises(argparse.ArgumentTypeError, match="Invalid mapping 'invalid'"):
        MODULE.parse_map_entries(["invalid"])


def test_ensure_import_respects_docstring_and_future(tmp_path: Path) -> None:
    source = Path("src/ratchetr/api.py")
    dest = tmp_path / "api.py"
    _ = shutil.copy2(source, dest)

    exit_code = MODULE.main([
        "--root",
        str(tmp_path),
        "--ensure-import",
        "api.py:tests.helpers:new_helper",
        "--apply",
    ])
    assert exit_code == 0
    contents = dest.read_text(encoding="utf-8").splitlines()
    injected_line = "from tests.helpers import new_helper"
    assert injected_line in contents
    future_idx = contents.index("from __future__ import annotations")
    injected_idx = contents.index(injected_line)
    assert injected_idx > future_idx


def test_export_map_updates_real_module(tmp_path: Path) -> None:
    source = Path("src/ratchetr/__init__.py")
    dest = tmp_path / "__init__.py"
    _ = shutil.copy2(source, dest)

    exit_code = MODULE.main([
        "--root",
        str(tmp_path),
        "--export-map",
        "run_audit=execute_audit",
        "--apply",
    ])
    assert exit_code == 0
    text = dest.read_text(encoding="utf-8")
    assert '"execute_audit"' in text


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(text, encoding="utf-8")


def test_git_discovery_limits_to_tracked_files(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    tracked = repo / "pkg" / "tracked.py"
    untracked = repo / "pkg" / "untracked.py"
    _write(tracked, "import alpha.module\n")
    _write(untracked, "import alpha.module\n")

    def _fake_tracked_python_files(root: Path) -> list[Path]:
        assert root == repo
        return [tracked]

    monkeypatch.setattr(MODULE, "_git_tracked_python_files", _fake_tracked_python_files)

    exit_code = MODULE.main([
        "--root",
        str(repo),
        "--map",
        "alpha.module=beta.module",
        "--apply",
    ])
    assert exit_code == 0
    assert tracked.read_text(encoding="utf-8") == "import beta.module\n"
    # Untracked file untouched because git discovery only lists tracked files
    assert untracked.read_text(encoding="utf-8") == "import alpha.module\n"


def test_no_use_git_processes_untracked_files(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    tracked = repo / "pkg" / "tracked.py"
    untracked = repo / "pkg" / "untracked.py"
    _write(tracked, "from source import item\n")
    _write(untracked, "from source import item\n")

    exit_code = MODULE.main([
        "--root",
        str(repo),
        "--map",
        "source=dest",
        "--no-use-git",
        "--apply",
    ])
    assert exit_code == 0
    assert tracked.read_text(encoding="utf-8") == "from dest import item\n"
    assert untracked.read_text(encoding="utf-8") == "from dest import item\n"
