# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

from __future__ import annotations

import runpy

import pytest


def test_main_module_invokes_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, object] = {}

    def fake_main() -> int:
        called["hit"] = True
        return 5

    monkeypatch.setattr("typewiz.cli.main", fake_main)
    with pytest.raises(SystemExit) as excinfo:
        _ = runpy.run_module("typewiz.__main__", run_name="__main__")
    assert excinfo.value.code == 5
    assert called["hit"] is True
