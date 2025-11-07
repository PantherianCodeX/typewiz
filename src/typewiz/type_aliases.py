# Copyright (c) 2024 PantherianCodeX

"""Typed aliases used across Typewiz internals."""

from __future__ import annotations

from typing import Literal, NewType

PathKey = NewType("PathKey", str)
CacheKey = NewType("CacheKey", str)
CategoryName = NewType("CategoryName", str)
RuleName = NewType("RuleName", str)
ToolName = NewType("ToolName", str)
EngineName = NewType("EngineName", str)
ProfileName = NewType("ProfileName", str)

CategoryKey = Literal["unknownChecks", "optionalChecks", "unusedSymbols", "general"]
RunId = NewType("RunId", str)
RunnerName = EngineName

__all__ = [
    "CacheKey",
    "CategoryKey",
    "CategoryName",
    "EngineName",
    "ProfileName",
    "PathKey",
    "RuleName",
    "RunnerName",
    "RunId",
    "ToolName",
]
