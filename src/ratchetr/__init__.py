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

"""ratchetr - Python Type Checker toolkit.

Provides utilities for collecting typing diagnostics from pyright, mypy, and
custom plugins, aggregating them into manifests and dashboards for progress
tracking.
"""

from __future__ import annotations

from ratchetr.exceptions import (
    RatchetrError,
    RatchetrTypeError,
    RatchetrValidationError,
)

from .api import (
    AuditResult,
    ManifestPayloadError,
    ManifestValidationResult,
    build_summary,
    emit_dashboard_outputs,
    load_manifest,
    load_summary_from_manifest,
    manifest_json_schema,
    render_dashboard_summary,
    render_html,
    render_markdown,
    run_audit,
    validate_manifest_file,
)
from .config import AuditConfig, Config, load_config
from .core.summary_types import SummaryData
from .core.types import Diagnostic, RunResult
from .manifest.typed import ToolSummary
from .ratchet import (
    apply_auto_update as ratchet_apply_auto_update,
)
from .ratchet import (
    build_ratchet_from_manifest as ratchet_build,
)
from .ratchet import (
    compare_manifest_to_ratchet as ratchet_compare,
)
from .ratchet import (
    refresh_signatures as ratchet_refresh,
)

__all__ = [
    "AuditConfig",
    "AuditResult",
    "Config",
    "Diagnostic",
    "ManifestPayloadError",
    "ManifestValidationResult",
    "RatchetrError",
    "RatchetrTypeError",
    "RatchetrValidationError",
    "RunResult",
    "SummaryData",
    "ToolSummary",
    "__version__",
    "build_summary",
    "emit_dashboard_outputs",
    "load_config",
    "load_manifest",
    "load_summary_from_manifest",
    "manifest_json_schema",
    "ratchet_apply_auto_update",
    "ratchet_build",
    "ratchet_compare",
    "ratchet_refresh",
    "render_dashboard_summary",
    "render_html",
    "render_markdown",
    "run_audit",
    "validate_manifest_file",
]

__version__ = "0.1.0"
