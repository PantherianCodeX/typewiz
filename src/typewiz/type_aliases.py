"""Typed aliases used across Typewiz internals."""

from __future__ import annotations

from typing import NewType

PathKey = NewType("PathKey", str)
CacheKey = NewType("CacheKey", str)
CategoryName = NewType("CategoryName", str)
RuleName = NewType("RuleName", str)

__all__ = ["CacheKey", "CategoryName", "PathKey", "RuleName"]
