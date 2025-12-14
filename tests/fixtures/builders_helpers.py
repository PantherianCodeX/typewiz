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

"""Helper builders for test fixtures."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Final

from ratchetr.core.model_types import ReadinessStatus, SeverityLevel
from ratchetr.core.type_aliases import ToolName
from ratchetr.core.types import Diagnostic

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from ratchetr.core.summary_types import (
        CountsByCategory,
        CountsByRule,
        CountsBySeverity,
        EnginesTab,
        HotspotsTab,
        OverviewTab,
        ReadinessOptionEntry,
        ReadinessStrictEntry,
        ReadinessTab,
        RunsTab,
        SummaryData,
        SummaryFileEntry,
        SummaryFolderEntry,
        SummaryRunEntry,
        SummaryTabs,
    )
    from ratchetr.core.type_aliases import CategoryKey, RunId

__all__ = [
    "DEFAULT_READINESS_CATEGORY",
    "TOOL_PYRIGHT",
    "TOOL_STUB",
    "build_diagnostic",
    "build_empty_summary",
    "build_readiness_summary",
]

TOOL_PYRIGHT: Final[ToolName] = ToolName("pyright")
TOOL_STUB: Final[ToolName] = ToolName("stub")
DEFAULT_READINESS_CATEGORY: CategoryKey = "unknownChecks"


def build_diagnostic(
    *,
    tool: ToolName | None = None,
    severity: SeverityLevel = SeverityLevel.ERROR,
    path: Path | str = "src/app.py",
    line: int = 1,
    column: int = 1,
    code: str = "reportGeneralTypeIssues",
    message: str = "example diagnostic",
) -> Diagnostic:
    """Build a `Diagnostic` fixture populated with test-friendly defaults.

    This helper reduces boilerplate in unit tests by providing stable defaults while
    allowing callers to override any field relevant to the scenario being tested.

    Args:
        tool: Optional tool identifier. Defaults to `TOOL_PYRIGHT` when omitted.
        severity: Severity level to assign to the diagnostic.
        path: Path associated with the diagnostic. Strings are converted to `Path`.
        line: 1-based line number associated with the diagnostic.
        column: 1-based column number associated with the diagnostic.
        code: Tool-specific rule/code identifier (for example, a pyright rule name).
        message: Human-readable diagnostic message.

    Returns:
        A `Diagnostic` instance populated with the provided values.
    """
    diag_tool = tool or TOOL_PYRIGHT
    diag_path = Path(path)
    return Diagnostic(
        tool=diag_tool,
        severity=severity,
        path=diag_path,
        line=line,
        column=column,
        code=code,
        message=message,
    )


def build_empty_summary() -> SummaryData:
    """Construct an empty `SummaryData` payload with valid required structure.

    This fixture is a baseline used by other builders that "fill in" specific tabs.
    It guarantees that all required keys and tab containers exist but contains no
    runs, diagnostics, or hotspot/readiness content.

    Returns:
        A structurally valid `SummaryData` skeleton with empty tabs and counts.
    """
    run_summary: dict[RunId, SummaryRunEntry] = {}
    severity_totals: CountsBySeverity = {}
    category_totals: CountsByCategory = {}
    top_rules: CountsByRule = {}
    overview: OverviewTab = {
        "severityTotals": severity_totals,
        "categoryTotals": category_totals,
        "runSummary": run_summary,
    }
    engines: EnginesTab = {"runSummary": run_summary}
    top_folders: list[SummaryFolderEntry] = []
    top_files: list[SummaryFileEntry] = []
    hotspots: HotspotsTab = {
        "topRules": top_rules,
        "topFolders": top_folders,
        "topFiles": top_files,
        "ruleFiles": {},
    }
    readiness: ReadinessTab = {
        "strict": {
            ReadinessStatus.READY: [],
            ReadinessStatus.CLOSE: [],
            ReadinessStatus.BLOCKED: [],
        },
        "options": {},
    }
    runs: RunsTab = {"runSummary": run_summary}
    tabs: SummaryTabs = {
        "overview": overview,
        "engines": engines,
        "hotspots": hotspots,
        "readiness": readiness,
        "runs": runs,
    }
    summary: SummaryData = {
        "generatedAt": "now",
        "projectRoot": ".",
        "runSummary": run_summary,
        "severityTotals": severity_totals,
        "categoryTotals": category_totals,
        "topRules": top_rules,
        "topFolders": top_folders,
        "topFiles": top_files,
        "ruleFiles": {},
        "tabs": tabs,
    }
    return summary


def build_readiness_summary(
    *,
    option_entries: Mapping[ReadinessStatus, Sequence[ReadinessOptionEntry]] | None = None,
    strict_entries: Mapping[ReadinessStatus, Sequence[ReadinessStrictEntry]] | None = None,
    category: CategoryKey = DEFAULT_READINESS_CATEGORY,
    threshold: int = 0,
) -> SummaryData:
    """Build a `SummaryData` fixture populated with readiness tab content.

    This helper starts from `build_empty_summary()` and injects readiness structures
    into `tabs.readiness`. It supports two independent readiness representations:

    - Option readiness buckets under `tabs.readiness.options[category]`
    - Strict readiness lists under `tabs.readiness.strict`

    Args:
        option_entries: Optional mapping of readiness status to option entries. When
            provided, entries are installed under `tabs.readiness.options[category]`
            and converted to the expected container types.
        strict_entries: Optional mapping of readiness status to strict entries. When
            provided, entries replace `tabs.readiness.strict`.
        category: Category key used when installing `option_entries` (for example,
            `"unknownChecks"`).
        threshold: Threshold value recorded alongside the option readiness buckets.

    Returns:
        A `SummaryData` payload containing readiness tab data derived from the supplied
        inputs.
    """
    summary = build_empty_summary()
    readiness_tab = summary["tabs"]["readiness"]
    if option_entries is not None:
        readiness_tab["options"] = {
            category: {
                "threshold": threshold,
                "buckets": {status: tuple(entries) for status, entries in option_entries.items()},
            },
        }
    if strict_entries is not None:
        readiness_tab["strict"] = {status: list(entries) for status, entries in strict_entries.items()}
    return summary
