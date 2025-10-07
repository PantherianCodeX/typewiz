from __future__ import annotations

from pathlib import Path

import pytest

from typewiz.utils import resolve_project_root


def test_resolve_project_root_prefers_local_markers(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    nested = workspace / "pkg"
    nested.mkdir(parents=True)
    (workspace / "typewiz.toml").write_text("config_version = 0\n", encoding="utf-8")

    assert resolve_project_root(nested) == workspace


def test_resolve_project_root_accepts_explicit_path_without_markers(tmp_path: Path) -> None:
    workspace = tmp_path / "explicit"
    workspace.mkdir()

    assert resolve_project_root(workspace) == workspace


def test_resolve_project_root_defaults_to_cwd_when_no_markers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    assert resolve_project_root() == tmp_path.resolve()
