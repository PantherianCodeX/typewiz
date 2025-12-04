# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Unit tests covering the manifest CLI command wiring."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest

from typewiz.cli.commands import manifest as manifest_cmd

pytestmark = [pytest.mark.unit, pytest.mark.cli]


def test_handle_schema_writes_requested_path(tmp_path: Path) -> None:
    # Arrange
    output = tmp_path / "schema.json"
    args = Namespace(indent=2, output=output, action="schema")

    # Act
    exit_code = manifest_cmd.execute_manifest(args)

    # Assert
    assert exit_code == 0
    assert output.exists()
    content = output.read_text(encoding="utf-8")
    assert content.startswith("{")
    assert content.rstrip().endswith("}")
