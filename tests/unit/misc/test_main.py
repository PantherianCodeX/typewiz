# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Unit tests for Misc Main."""

from __future__ import annotations

import runpy

import pytest

pytestmark = pytest.mark.unit


def test_main_module_invokes_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    called: dict[str, object] = {}

    def fake_main() -> int:
        called["hit"] = True
        return 5

    monkeypatch.setattr("typewiz.cli.main", fake_main)
    with pytest.raises(SystemExit, match=r".*") as excinfo:
        _ = runpy.run_module("typewiz.__main__", run_name="__main__")
    assert excinfo.value.code == 5
    assert called["hit"] is True
