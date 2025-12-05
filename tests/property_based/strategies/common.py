# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Shared Hypothesis strategies for property-based tests."""

from __future__ import annotations

from hypothesis import strategies as st

__all__ = [
    "arbitrary_cli_noise",
    "path_parts",
    "path_strings",
    "severity_counts",
]


def path_strings(min_size: int = 1, max_size: int = 20) -> st.SearchStrategy[str]:
    """Return a strategy that yields short POSIX path fragments."""
    return st.text(min_size=min_size, max_size=max_size)


def path_parts(min_size: int = 1, max_size: int = 5) -> st.SearchStrategy[list[str]]:
    """Return a strategy that yields lists of POSIX-like segments."""
    segment = st.from_regex(r"[a-zA-Z0-9_/]+", fullmatch=True)
    return st.lists(segment, min_size=min_size, max_size=max_size)


def severity_counts(max_value: int = 10) -> st.SearchStrategy[int]:
    """Strategy that emits bounded non-negative severity counts.

    Args:
        max_value: Maximum count allowed in the emitted integers.

    Returns:
        Hypothesis strategy producing integers between 0 and ``max_value``.
    """
    return st.integers(min_value=0, max_value=max_value)


def arbitrary_cli_noise() -> st.SearchStrategy[object]:
    """Inputs that should coerce to defaults in CLI helpers.

    Returns:
        Hypothesis strategy emitting arbitrary noise values (str/int/None).
    """
    return st.one_of(st.text(), st.integers(), st.none())
