# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Unit tests for CLI type helpers."""

from __future__ import annotations

from typewiz.cli import types


def test_subparser_collection_exported_via_all() -> None:
    """Ensure the shared CLI protocol is publicly re-exported."""
    assert "SubparserCollection" in types.__all__
