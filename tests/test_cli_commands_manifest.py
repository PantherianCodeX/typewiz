# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from typewiz.cli.commands import manifest as manifest_cmd


def test_handle_schema_writes_requested_path(tmp_path: Path) -> None:
    output = tmp_path / "schema.json"
    args = Namespace(indent=2, output=output)

    args.action = "schema"
    exit_code = manifest_cmd.execute_manifest(args)

    assert exit_code == 0
    assert output.exists()
    content = output.read_text(encoding="utf-8")
    assert content.startswith("{")
    assert content.rstrip().endswith("}")
