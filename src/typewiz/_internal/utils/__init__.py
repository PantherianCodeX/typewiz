"""Structured utility helpers used across Typewiz internals."""

from __future__ import annotations

from .common import consume
from .json import (
    JSONList,
    JSONMapping,
    JSONValue,
    as_int,
    as_list,
    as_mapping,
    as_str,
    normalise_enums_for_json,
    require_json,
)
from .locks import file_lock
from .paths import ROOT_MARKERS, RootMarker, default_full_paths, resolve_project_root
from .process import CommandOutput, python_executable, run_command
from .versions import detect_tool_versions

__all__ = [
    "CommandOutput",
    "JSONList",
    "JSONMapping",
    "JSONValue",
    "ROOT_MARKERS",
    "RootMarker",
    "as_int",
    "as_list",
    "as_mapping",
    "as_str",
    "consume",
    "default_full_paths",
    "detect_tool_versions",
    "file_lock",
    "normalise_enums_for_json",
    "python_executable",
    "require_json",
    "resolve_project_root",
    "run_command",
]
