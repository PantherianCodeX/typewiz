from __future__ import annotations

import argparse
import importlib.util
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
