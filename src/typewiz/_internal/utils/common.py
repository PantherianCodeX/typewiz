# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Small shared helpers used across utils modules."""

from __future__ import annotations

__all__ = ["consume"]


def consume(value: object | None) -> None:
    """Explicitly mark a value as intentionally unused."""
    _ = value
