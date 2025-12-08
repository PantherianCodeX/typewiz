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

"""Public API façade for ratchetr orchestration helpers."""

from __future__ import annotations

from ratchetr.dashboard import build_summary, load_manifest
from ratchetr.dashboard.render_html import render_html
from ratchetr.dashboard.render_markdown import render_markdown
from ratchetr.services.audit import AuditResult, run_audit
from ratchetr.services.dashboard import (
    emit_dashboard_outputs,
    load_summary_from_manifest,
    render_dashboard_summary,
)
from ratchetr.services.manifest import (
    ManifestPayloadError,
    ManifestValidationResult,
    manifest_json_schema,
    validate_manifest_file,
)

__all__ = [
    "AuditResult",
    "ManifestPayloadError",
    "ManifestValidationResult",
    "build_summary",
    "emit_dashboard_outputs",
    "load_manifest",
    "load_summary_from_manifest",
    "manifest_json_schema",
    "render_dashboard_summary",
    "render_html",
    "render_markdown",
    "run_audit",
    "validate_manifest_file",
]
