# Copyright 2025 CrownOps Engineering
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Shared helper utilities for the ratchetr CLI."""

from __future__ import annotations

from .args import (
    ArgumentRegistrar,
    collect_plugin_args,
    collect_profile_args,
    normalise_modes,
    parse_comma_separated,
    parse_hash_workers,
    parse_int_mapping,
    parse_key_value_entries,
    register_argument,
)
from .context import CLIContext, build_cli_context, discover_manifest_or_exit, emit_manifest_diagnostics
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
from .options import (
    READINESS_TOKENS_HELP,
    ReadinessOptions,
    SaveFlag,
    StdoutFormat,
    build_path_overrides,
    finalise_targets,
    parse_readiness_tokens,
    parse_save_flag,
    register_output_options,
    register_path_overrides,
    register_readiness_flag,
    register_save_flag,
)
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
    "DEFAULT_RATCHET_FILENAME",
    "DEFAULT_SEVERITIES",
    "MANIFEST_CANDIDATE_NAMES",
    "READINESS_TOKENS_HELP",
    "SUMMARY_FIELD_CHOICES",
    "ArgumentRegistrar",
    "CLIContext",
    "ReadinessOptions",
    "SaveFlag",
    "StdoutFormat",
    "apply_target_overrides",
    "build_cli_context",
    "build_path_overrides",
    "collect_plugin_args",
    "collect_profile_args",
    "discover_manifest_or_exit",
    "discover_manifest_path",
    "discover_ratchet_path",
    "echo",
    "emit_manifest_diagnostics",
    "ensure_parent",
    "finalise_targets",
    "format_list",
    "normalise_modes",
    "normalise_runs",
    "parse_comma_separated",
    "parse_hash_workers",
    "parse_int_mapping",
    "parse_key_value_entries",
    "parse_readiness_tokens",
    "parse_save_flag",
    "parse_summary_fields",
    "parse_target_entries",
    "print_readiness_summary",
    "print_summary",
    "query_engines",
    "query_hotspots",
    "query_overview",
    "query_readiness",
    "query_rules",
    "query_runs",
    "register_argument",
    "register_output_options",
    "register_path_overrides",
    "register_readiness_flag",
    "register_save_flag",
    "render_data",
    "resolve_limit",
    "resolve_path",
    "resolve_runs",
    "resolve_severities",
    "resolve_signature_policy",
    "resolve_summary_only",
    "split_target_mapping",
]
