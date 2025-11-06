# Copyright (c) 2024 PantherianCodeX
"""Argument parser helpers used across CLI commands."""

from __future__ import annotations

import argparse
from typing import Any, Protocol

from typewiz.utils import consume


class ArgumentRegistrar(Protocol):
    def add_argument(
        self, *args: Any, **kwargs: Any
    ) -> argparse.Action: ...  # pragma: no cover - stub


def register_argument(
    registrar: ArgumentRegistrar,
    *args: Any,
    **kwargs: Any,
) -> None:
    """Register an argument on a parser/argument group, discarding the action handle."""
    consume(registrar.add_argument(*args, **kwargs))


__all__ = ["ArgumentRegistrar", "register_argument"]
