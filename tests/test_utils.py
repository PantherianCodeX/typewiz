# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest

from typewiz._internal.utils import consume, normalise_enums_for_json, resolve_project_root
from typewiz.core.model_types import ReadinessStatus, SeverityLevel


def test_resolve_project_root_prefers_local_markers(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    nested = workspace / "pkg"
    nested.mkdir(parents=True)
    consume((workspace / "typewiz.toml").write_text("config_version = 0\n", encoding="utf-8"))

    assert resolve_project_root(nested) == workspace


def test_resolve_project_root_accepts_explicit_path_without_markers(tmp_path: Path) -> None:
    workspace = tmp_path / "explicit"
    workspace.mkdir()

    assert resolve_project_root(workspace) == workspace


def test_resolve_project_root_defaults_to_cwd_when_no_markers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    assert resolve_project_root() == tmp_path.resolve()


def test_normalise_enums_for_json_converts_keys_and_nested_values() -> None:
    payload = {
        ReadinessStatus.READY: {
            "status": ReadinessStatus.CLOSE,
            "counts": (ReadinessStatus.BLOCKED,),
        },
        "nested": [{"severity": SeverityLevel.ERROR}],
    }
    normalised = normalise_enums_for_json(payload)
    assert isinstance(normalised, dict)
    normalised_dict = cast(dict[str, object], normalised)
    ready_raw = normalised_dict.get("ready")
    assert isinstance(ready_raw, dict)
    ready_bucket = cast(dict[str, object], ready_raw)
    assert ready_bucket.get("status") == "close"
    counts_value = ready_bucket.get("counts")
    assert isinstance(counts_value, list) and counts_value
    assert counts_value[0] == "blocked"
    nested_raw = normalised_dict.get("nested")
    assert isinstance(nested_raw, list) and nested_raw
    first_nested = cast(dict[str, object], nested_raw[0])
    assert first_nested.get("severity") == "error"
