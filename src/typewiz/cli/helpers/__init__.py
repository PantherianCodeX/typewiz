# Copyright (c) 2024 PantherianCodeX
"""Shared helper utilities for the typewiz CLI."""

from __future__ import annotations

from .args import ArgumentRegistrar, register_argument
from .formatting import (
    SUMMARY_FIELD_CHOICES,
    format_list,
    parse_summary_fields,
    print_readiness_summary,
    print_summary,
    query_engines,
    query_hotspots,
    query_overview,
    query_readiness,
    query_rules,
    query_runs,
    render_data,
)
from .io import echo
from .ratchet import (
    DEFAULT_RATCHET_FILENAME,
    DEFAULT_SEVERITIES,
    MANIFEST_CANDIDATE_NAMES,
    apply_target_overrides,
    discover_manifest_path,
    discover_ratchet_path,
    ensure_parent,
    normalise_runs,
    parse_target_entries,
    resolve_limit,
    resolve_path,
    resolve_runs,
    resolve_severities,
    resolve_signature_policy,
    resolve_summary_only,
    split_target_mapping,
)

__all__ = [
    "ArgumentRegistrar",
    "DEFAULT_RATCHET_FILENAME",
    "DEFAULT_SEVERITIES",
    "MANIFEST_CANDIDATE_NAMES",
    "apply_target_overrides",
    "discover_manifest_path",
    "discover_ratchet_path",
    "echo",
    "ensure_parent",
    "format_list",
    "normalise_runs",
    "parse_target_entries",
    "parse_summary_fields",
    "print_readiness_summary",
    "print_summary",
    "query_engines",
    "query_hotspots",
    "query_overview",
    "query_readiness",
    "query_rules",
    "query_runs",
    "register_argument",
    "resolve_limit",
    "resolve_path",
    "resolve_runs",
    "resolve_severities",
    "resolve_signature_policy",
    "resolve_summary_only",
    "render_data",
    "split_target_mapping",
    "SUMMARY_FIELD_CHOICES",
]
