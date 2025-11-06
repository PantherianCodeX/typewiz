# Copyright (c) 2024 PantherianCodeX
"""IO helpers for CLI output."""

from __future__ import annotations

import sys
from typing import TextIO

from typewiz.utils import consume


def _select_stream(*, err: bool = False) -> TextIO:
    return sys.stderr if err else sys.stdout


def echo(message: str, *, newline: bool = True, err: bool = False) -> None:
    """Write a message to stdout/stderr, mirroring legacy CLI behaviour."""
    stream = _select_stream(err=err)
    consume(stream.write(message))
    if newline:
        consume(stream.write("\n"))


__all__ = ["echo"]
