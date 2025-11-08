from __future__ import annotations

import argparse
import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "refactor_imports.py"
SPEC = importlib.util.spec_from_file_location("refactor_imports", MODULE_PATH)
assert SPEC and SPEC.loader
_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = _module
SPEC.loader.exec_module(_module)
MODULE: Any = _module


def test_rewrite_content_updates_from_import() -> None:
    content = "from foo.bar import Baz\n"
    new_content, changed = MODULE._rewrite_content(content, {"foo.bar": "new.mod"})
    assert changed
    assert new_content == "from new.mod import Baz\n"


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
    with pytest.raises(argparse.ArgumentTypeError):
        MODULE._parse_map_entries(["invalid"])


def test_ensure_import_respects_docstring_and_future(tmp_path: Path) -> None:
    source = Path("src/typewiz/api.py")
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
    source = Path("src/typewiz/__init__.py")
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


def _init_repo(path: Path) -> None:
    _ = subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    _ = subprocess.run(
        ["git", "config", "user.name", "Codex"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    _ = subprocess.run(
        ["git", "config", "user.email", "codex@example.com"],
        cwd=path,
        check=True,
        capture_output=True,
    )


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(text, encoding="utf-8")


def test_git_discovery_limits_to_tracked_files(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _init_repo(repo)
    tracked = repo / "pkg" / "tracked.py"
    untracked = repo / "pkg" / "untracked.py"
    _write(tracked, "import alpha.module\n")
    _write(untracked, "import alpha.module\n")
    _ = subprocess.run(["git", "add", str(tracked.relative_to(repo))], cwd=repo, check=True)
    _ = subprocess.run(
        ["git", "commit", "-m", "add tracked"], cwd=repo, check=True, capture_output=True
    )

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
    _init_repo(repo)
    tracked = repo / "pkg" / "tracked.py"
    untracked = repo / "pkg" / "untracked.py"
    _write(tracked, "from source import item\n")
    _write(untracked, "from source import item\n")
    _ = subprocess.run(["git", "add", str(tracked.relative_to(repo))], cwd=repo, check=True)
    _ = subprocess.run(
        ["git", "commit", "-m", "add tracked"], cwd=repo, check=True, capture_output=True
    )

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
