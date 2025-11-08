# Copyright (c) 2024 PantherianCodeX

"""Typed aliases used across Typewiz internals."""

from __future__ import annotations

from typing import Literal, NewType

type Command = list[str]

PathKey = NewType("PathKey", str)
CacheKey = NewType("CacheKey", str)
CategoryName = NewType("CategoryName", str)
RuleName = NewType("RuleName", str)
ToolName = NewType("ToolName", str)
EngineName = NewType("EngineName", str)
ProfileName = NewType("ProfileName", str)
RelPath = NewType("RelPath", str)

CategoryKey = Literal["unknownChecks", "optionalChecks", "unusedSymbols", "general"]
BuiltinEngineName = Literal["pyright", "mypy"]
RunId = NewType("RunId", str)
RunnerName = EngineName

__all__ = [
    "Command",
    "BuiltinEngineName",
    "CacheKey",
    "CategoryKey",
    "CategoryName",
    "EngineName",
    "ProfileName",
    "RelPath",
    "PathKey",
    "RuleName",
    "RunnerName",
    "RunId",
    "ToolName",
]
