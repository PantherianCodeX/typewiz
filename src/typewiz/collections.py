# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Public collections helpers (stable shim over internal implementations)."""

from __future__ import annotations

from typewiz._internal.collection_utils import dedupe_preserve, merge_preserve

__all__ = [
    "dedupe_preserve",
    "merge_preserve",
]
