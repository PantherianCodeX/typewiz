# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest

from typewiz.cli.commands import cache as cache_cmd


def test_handle_clear_removes_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / ".typewiz_cache"
    target.mkdir()

    def fake_resolve_root(value: Path | None) -> Path:
        assert value is None
        return tmp_path

    monkeypatch.setattr(cache_cmd, "resolve_project_root", fake_resolve_root)
    args = Namespace(cache_action="clear", path=target, project_root=None)
    exit_code = cache_cmd.execute_cache(args)
    assert exit_code == 0
    assert not target.exists()


def test_handle_clear_handles_missing_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    args = Namespace(cache_action="clear", path=tmp_path / "missing", project_root=None)

    def fake_root(_: object) -> Path:
        return tmp_path

    monkeypatch.setattr(cache_cmd, "resolve_project_root", fake_root)
    exit_code = cache_cmd.execute_cache(args)
    assert exit_code == 0


def test_execute_cache_unknown_action() -> None:
    with pytest.raises(SystemExit):
        _ = cache_cmd.execute_cache(Namespace(cache_action="invalid"))
