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

"""Test data builders live here until dedicated modules are created."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ratchetr._infra.utils import consume
from ratchetr.core.model_types import Mode, OverrideEntry, ReadinessStatus, SeverityLevel
from ratchetr.core.summary_types import (
    CountsByCategory,
    CountsByRule,
    CountsBySeverity,
    ReadinessOptionEntry,
    ReadinessOptionsPayload,
    ReadinessStrictEntry,
    ReadinessTab,
    RulePathEntry,
    SummaryData,
    SummaryFileEntry,
    SummaryFolderEntry,
    SummaryRunEntry,
    SummaryTabs,
)
from ratchetr.core.type_aliases import CategoryName, RelPath, RunId, ToolName
from ratchetr.core.types import Diagnostic, RunResult
from ratchetr.manifest.versioning import CURRENT_MANIFEST_VERSION
from tests.fixtures.builders_helpers import (
    TOOL_PYRIGHT,
    TOOL_STUB,
    build_diagnostic,
    build_empty_summary,
    build_readiness_summary,
)

if TYPE_CHECKING:
    from ratchetr.readiness.compute import ReadinessEntry

__all__ = [
    "TestDataBuilder",
    "build_cli_manifest",
    "build_cli_run_result",
    "build_cli_summary",
    "build_diagnostic",
    "build_empty_summary",
    "build_readiness_entries",
    "build_readiness_summary",
    "build_sample_run",
    "build_sample_summary",
]


@dataclass(slots=True)
class TestDataBuilder:
    """Factory for rich sample payloads used in tests.

    Attributes:
        project_root: Default project root inserted into generated payloads.
        generated_at: Timestamp string used for deterministic fixtures.
        tool_name: Default tool identifier used when building diagnostics/runs.
        stub_tool_name: Secondary tool identifier used by stubbed fixtures.

    Returns:
        A `SummaryData` payload seeded with deterministic values for CLI tests.
    """

    __test__ = False

    project_root: Path = Path("/repo")
    generated_at: str = "2025-01-01T00:00:00Z"
    tool_name: ToolName = TOOL_PYRIGHT
    stub_tool_name: ToolName = TOOL_STUB

    def build_sample_summary(self) -> SummaryData:
        """Construct a representative `SummaryData` payload for dashboard tests.

        This method builds a “rich” summary containing multiple populated tabs
        (overview, engines, hotspots, readiness, runs). It is intended to exercise
        dashboard rendering and summary aggregation paths with realistic-looking data.

        Returns:
            A synthetic `SummaryData` payload suitable for dashboard-oriented tests.
        """
        pyright_override, mypy_override = self._build_sample_overrides()
        run_summary = self._build_sample_run_summary(
            pyright_override=pyright_override,
            mypy_override=mypy_override,
        )

        severity_totals: CountsBySeverity = {
            SeverityLevel.ERROR: 1,
            SeverityLevel.WARNING: 1,
            SeverityLevel.INFORMATION: 0,
        }
        top_rules: CountsByRule = {
            "reportUnknownMemberType": 1,
            "reportGeneralTypeIssues": 1,
        }
        ready_code_counts: dict[str, int] = {}
        agent_code_counts: dict[str, int] = {"reportUnknownParameterType": 1}
        top_folders: list[SummaryFolderEntry] = [
            {
                "path": "apps/platform/operations",
                "errors": 0,
                "warnings": 0,
                "information": 0,
                "participatingRuns": 1,
                "codeCounts": ready_code_counts,
                "recommendations": ["strict-ready"],
            },
            {
                "path": "packages/agents",
                "errors": 1,
                "warnings": 1,
                "information": 0,
                "participatingRuns": 1,
                "codeCounts": agent_code_counts,
                "recommendations": ["resolve 1 unknown-type issues"],
            },
        ]
        top_files: list[SummaryFileEntry] = [
            {
                "path": "apps/platform/operations/admin.py",
                "errors": 0,
                "warnings": 0,
                "information": 0,
            },
            {
                "path": "packages/core/agents.py",
                "errors": 1,
                "warnings": 1,
                "information": 0,
            },
        ]
        rule_files: dict[str, list[RulePathEntry]] = {
            "reportGeneralTypeIssues": [RulePathEntry(path="packages/core/agents.py", count=1)],
            "reportUnknownMemberType": [RulePathEntry(path="packages/core/agents.py", count=1)],
        }

        readiness_tab = self._build_sample_readiness_tab()
        category_totals: CountsByCategory = {}
        tabs = self._build_sample_tabs(
            severity_totals=severity_totals,
            category_totals=category_totals,
            run_summary=run_summary,
            top_rules=top_rules,
            top_folders=top_folders,
            top_files=top_files,
            rule_files=rule_files,
            readiness_tab=readiness_tab,
        )

        return {
            "generatedAt": self.generated_at,
            "projectRoot": self.project_root.as_posix(),
            "runSummary": run_summary,
            "severityTotals": severity_totals,
            "categoryTotals": category_totals,
            "topRules": top_rules,
            "topFolders": top_folders,
            "topFiles": top_files,
            "ruleFiles": rule_files,
            "tabs": tabs,
        }

    @staticmethod
    def _build_sample_overrides() -> tuple[OverrideEntry, OverrideEntry]:
        """Return the canonical overrides used across sample summaries."""
        pyright_override: OverrideEntry = {
            "path": "apps/platform",
            "pluginArgs": ["--warnings"],
        }
        mypy_override: OverrideEntry = {
            "path": "packages/legacy",
            "exclude": [RelPath("packages/legacy")],
        }
        return pyright_override, mypy_override

    @staticmethod
    def _build_sample_run_summary(
        *,
        pyright_override: OverrideEntry,
        mypy_override: OverrideEntry,
    ) -> dict[RunId, SummaryRunEntry]:
        """Construct the run summary shared across tabs.

        Returns:
            Mapping from `RunId`to synthetic `SummaryRunEntry`payloads
            used by dashboard and CLI workflow tests.
        """
        return {
            RunId("pyright:current"): {
                "command": ["pyright", "--outputjson"],
                "errors": 0,
                "warnings": 0,
                "information": 0,
                "total": 0,
                "engineOptions": {
                    "profile": "baseline",
                    "configFile": "pyrightconfig.json",
                    "pluginArgs": ["--lib"],
                    "include": [RelPath("apps")],
                    "exclude": [RelPath("apps/legacy")],
                    "overrides": [pyright_override],
                },
            },
            RunId("mypy:target"): {
                "command": ["python", "-m", "mypy"],
                "errors": 1,
                "warnings": 1,
                "information": 0,
                "total": 2,
                "engineOptions": {
                    "profile": "strict",
                    "configFile": "mypy.ini",
                    "pluginArgs": ["--strict"],
                    "include": [RelPath("packages")],
                    "exclude": [],
                    "overrides": [mypy_override],
                },
            },
        }

    @staticmethod
    def _build_sample_readiness_tab() -> ReadinessTab:
        """Generate readiness data used by dashboard and CLI tests.

        Returns:
            `ReadinessTab`payload containing strict and per-option
            readiness data for a representative project.
        """

        def _bucket(
            ready: list[ReadinessOptionEntry],
            close: list[ReadinessOptionEntry],
            *,
            threshold: int,
        ) -> ReadinessOptionsPayload:
            buckets: dict[ReadinessStatus, tuple[ReadinessOptionEntry, ...]] = {}
            if ready:
                buckets[ReadinessStatus.READY] = tuple(ready)
            if close:
                buckets[ReadinessStatus.CLOSE] = tuple(close)
            return {
                "threshold": threshold,
                "buckets": buckets,
            }

        readiness_ready_categories: dict[CategoryName, int] = {
            CategoryName("unknownChecks"): 0,
            CategoryName("optionalChecks"): 0,
            CategoryName("unusedSymbols"): 0,
            CategoryName("general"): 0,
        }
        readiness_ready_status: dict[CategoryName, ReadinessStatus] = {
            CategoryName("unknownChecks"): ReadinessStatus.READY,
            CategoryName("optionalChecks"): ReadinessStatus.READY,
            CategoryName("unusedSymbols"): ReadinessStatus.READY,
            CategoryName("general"): ReadinessStatus.READY,
        }
        readiness_ready: list[ReadinessStrictEntry] = [
            {
                "path": "apps/platform/operations",
                "errors": 0,
                "warnings": 0,
                "information": 0,
                "diagnostics": 0,
                "categories": readiness_ready_categories,
                "categoryStatus": readiness_ready_status,
                "recommendations": ["strict-ready"],
            },
        ]
        readiness_close_categories: dict[CategoryName, int] = {
            CategoryName("unknownChecks"): 1,
            CategoryName("optionalChecks"): 0,
            CategoryName("unusedSymbols"): 0,
            CategoryName("general"): 0,
        }
        readiness_close_status: dict[CategoryName, ReadinessStatus] = {
            CategoryName("unknownChecks"): ReadinessStatus.CLOSE,
            CategoryName("optionalChecks"): ReadinessStatus.READY,
            CategoryName("unusedSymbols"): ReadinessStatus.READY,
            CategoryName("general"): ReadinessStatus.READY,
        }
        readiness_close: list[ReadinessStrictEntry] = [
            {
                "path": "packages/agents",
                "errors": 1,
                "warnings": 1,
                "information": 0,
                "diagnostics": 2,
                "categories": readiness_close_categories,
                "categoryStatus": readiness_close_status,
                "recommendations": ["resolve 1 unknown-type issues"],
                "notes": ["unknownChecks: 1"],
            },
        ]

        return {
            "strict": {
                ReadinessStatus.READY: readiness_ready,
                ReadinessStatus.CLOSE: readiness_close,
                ReadinessStatus.BLOCKED: [],
            },
            "options": {
                "unknownChecks": _bucket(
                    ready=[
                        {
                            "path": "apps/platform/operations",
                            "count": 0,
                            "errors": 0,
                            "warnings": 0,
                        },
                    ],
                    close=[{"path": "packages/agents", "count": 1, "errors": 1, "warnings": 1}],
                    threshold=2,
                ),
                "optionalChecks": _bucket(
                    ready=[
                        {
                            "path": "apps/platform/operations",
                            "count": 0,
                            "errors": 0,
                            "warnings": 0,
                        },
                    ],
                    close=[],
                    threshold=2,
                ),
                "unusedSymbols": _bucket(
                    ready=[
                        {
                            "path": "apps/platform/operations",
                            "count": 0,
                            "errors": 0,
                            "warnings": 0,
                        },
                    ],
                    close=[],
                    threshold=4,
                ),
                "general": _bucket(
                    ready=[
                        {
                            "path": "apps/platform/operations",
                            "count": 0,
                            "errors": 0,
                            "warnings": 0,
                        },
                    ],
                    close=[],
                    threshold=5,
                ),
            },
        }

    @staticmethod
    # ignore JUSTIFIED: test data builder requires explicit keyword-only inputs for
    # readability; many keyword parameters reflect the shape of the readiness dashboard
    # payload
    def _build_sample_tabs(  # noqa: PLR0913
        *,
        severity_totals: CountsBySeverity,
        category_totals: CountsByCategory,
        run_summary: dict[RunId, SummaryRunEntry],
        top_rules: CountsByRule,
        top_folders: list[SummaryFolderEntry],
        top_files: list[SummaryFileEntry],
        rule_files: dict[str, list[RulePathEntry]],
        readiness_tab: ReadinessTab,
    ) -> SummaryTabs:
        """Assemble SummaryTabs shared across CLI/dashboard tests.

        Returns:
            Complete `SummaryTabs`mapping for use in CLI and dashboard
            integration tests.
        """
        return {
            "overview": {
                "severityTotals": severity_totals,
                "categoryTotals": category_totals,
                "runSummary": run_summary,
            },
            "engines": {"runSummary": run_summary},
            "hotspots": {
                "topRules": top_rules,
                "topFolders": top_folders,
                "topFiles": top_files,
                "ruleFiles": rule_files,
            },
            "readiness": readiness_tab,
            "runs": {"runSummary": run_summary},
        }

    def build_cli_summary(self) -> SummaryData:
        """Construct a `SummaryData` payload tailored to CLI helper tests.

        This fixture favors determinism and minimal-but-valid structure while still
        populating the fields commonly exercised by CLI formatting logic (overview,
        hotspots, readiness, run metadata).

        Returns:
            A deterministic `SummaryData` fixture suitable for CLI-facing tests.
        """
        readiness_tab: ReadinessTab = {
            "strict": {
                ReadinessStatus.BLOCKED: [
                    {
                        "path": "src/app.py",
                        "diagnostics": 2,
                        "errors": 1,
                        "warnings": 1,
                        "information": 0,
                    }
                ],
                ReadinessStatus.READY: [],
                ReadinessStatus.CLOSE: [],
            },
            "options": {
                "unknownChecks": ReadinessOptionsPayload(
                    threshold=1,
                    buckets={
                        ReadinessStatus.BLOCKED: (ReadinessOptionEntry(path="src", count=2, errors=1, warnings=1),),
                    },
                ),
            },
        }
        severity_totals: CountsBySeverity = {SeverityLevel.ERROR: 2}
        category_totals: CountsByCategory = {"unknownChecks": 2}
        top_rules: CountsByRule = {}
        run_id = RunId("pyright:current")
        summary: SummaryData = {
            "generatedAt": self.generated_at,
            "projectRoot": self.project_root.as_posix(),
            "severityTotals": severity_totals,
            "categoryTotals": category_totals,
            "runSummary": {},
            "topFolders": [],
            "topFiles": [],
            "topRules": top_rules,
            "ruleFiles": {
                "reportGeneralTypeIssues": [RulePathEntry(path="src/app.py", count=2)],
            },
            "tabs": {
                "overview": {
                    "severityTotals": severity_totals,
                    "categoryTotals": category_totals,
                    "runSummary": {
                        run_id: {
                            "errors": 1,
                            "warnings": 0,
                            "information": 1,
                            "total": 2,
                        }
                    },
                },
                "hotspots": {
                    "topFiles": [
                        {
                            "path": "src/app.py",
                            "errors": 1,
                            "warnings": 0,
                            "information": 0,
                        }
                    ],
                    "topFolders": [
                        {
                            "path": "src",
                            "errors": 1,
                            "warnings": 0,
                            "information": 1,
                            "participatingRuns": 1,
                            "codeCounts": {"reportGeneralTypeIssues": 1},
                            "recommendations": ["add types"],
                        }
                    ],
                    "topRules": {"reportGeneralTypeIssues": 2},
                    "ruleFiles": {
                        "reportGeneralTypeIssues": [RulePathEntry(path="src/app.py", count=2)],
                    },
                },
                "readiness": readiness_tab,
                "runs": {
                    "runSummary": {
                        run_id: {
                            "errors": 1,
                            "warnings": 0,
                            "information": 1,
                            "command": ["pyright", "--strict"],
                        }
                    }
                },
                "engines": {
                    "runSummary": {
                        run_id: {
                            "engineOptions": {
                                "profile": "strict",
                                "configFile": "pyrightconfig.json",
                                "pluginArgs": ["--strict"],
                                "include": [RelPath("src")],
                                "exclude": [],
                                "overrides": [],
                            }
                        }
                    }
                },
            },
        }
        return summary

    def build_cli_run_result(self) -> RunResult:
        """Construct a `RunResult` fixture tailored to CLI printing tests.

        The returned run includes representative metadata and at least one diagnostic
        so downstream code paths (formatting, grouping, rendering) are exercised.

        Returns:
            A deterministic `RunResult` seeded with representative diagnostics and
            engine metadata for CLI tests.
        """
        diagnostic = Diagnostic(
            tool=self.tool_name,
            severity=SeverityLevel.ERROR,
            path=Path("src/app.py"),
            line=1,
            column=1,
            code="E100",
            message="boom",
        )
        run = RunResult(
            tool=self.tool_name,
            mode=Mode.CURRENT,
            command=["pyright", "--strict"],
            exit_code=1,
            duration_ms=1.0,
            diagnostics=[diagnostic],
            profile="strict",
            config_file=Path("pyrightconfig.json"),
        )
        run.plugin_args = ["--strict"]
        run.include = [RelPath("src")]
        run.exclude = [RelPath("tests")]
        return run

    @staticmethod
    def build_readiness_entries(count: int = 200) -> list[ReadinessEntry]:
        """Generate synthetic readiness entries for readiness computation tests.

        The generated entries vary counts deterministically to provide a stable but
        non-trivial dataset for readiness scoring and bucketing logic.

        Args:
            count: Number of readiness records to generate.

        Returns:
            A list of synthetic readiness entries.
        """
        entries: list[ReadinessEntry] = []
        for index in range(count):
            unknown_count = (index * 3) % 5
            optional_count = (index * 2) % 4
            entries.append(
                {
                    "path": f"pkg/module_{index}.py",
                    "errors": index % 3,
                    "warnings": (index + 1) % 5,
                    "information": 0,
                    "codeCounts": {
                        f"reportUnknown{index % 4}": unknown_count,
                        f"optionalCheck{index % 5}": optional_count,
                    },
                    "categoryCounts": {},
                    "recommendations": [],
                },
            )
        return entries

    def build_sample_run(
        self,
        num_files: int = 120,
        diagnostics_per_file: int = 5,
        *,
        tool_name: ToolName | None = None,
    ) -> RunResult:
        """Construct a `RunResult` containing many diagnostics for performance tests.

        This fixture is intended for benchmarking and stress testing summary/aggregation
        code paths by generating `num_files * diagnostics_per_file` diagnostics.

        Args:
            num_files: Number of distinct file paths to include in the run.
            diagnostics_per_file: Number of diagnostics to generate per file.
            tool_name: Optional override for the tool identifier used in diagnostics.

        Returns:
            A `RunResult` containing synthetic diagnostics suitable for performance tests.
        """
        diagnostics: list[Diagnostic] = []
        target_tool = tool_name or self.tool_name
        for file_index in range(num_files):
            path = Path(f"pkg/module_{file_index}.py")
            diagnostics.extend(
                Diagnostic(
                    tool=target_tool,
                    severity=(SeverityLevel.ERROR if not diag_index % 3 else SeverityLevel.WARNING),
                    path=path,
                    line=diag_index + 1,
                    column=1,
                    code=f"reportUnknown{diag_index % 4}",
                    message="example diagnostic",
                )
                for diag_index in range(diagnostics_per_file)
            )
        return RunResult(
            tool=target_tool,
            mode=Mode.CURRENT,
            command=["pyright"],
            exit_code=0,
            duration_ms=0.0,
            diagnostics=diagnostics,
            category_mapping={"unknownChecks": ["reportunknown"], "optionalChecks": ["optional"]},
        )


_DEFAULT_TEST_DATA_BUILDER = TestDataBuilder()


def build_sample_summary() -> SummaryData:
    """Build a rich `SummaryData` fixture for dashboard-style tests.

    This is the preferred entry point for tests that validate dashboard rendering,
    tab composition, and summary aggregation behavior. The returned payload is:

    - Structurally complete (all expected top-level keys and tabs present).
    - Deterministic (stable timestamps/paths) to support snapshot and golden tests.
    - Representative (non-trivial hotspots/readiness content) to exercise UI logic.

    Returns:
        A rich, structurally complete `SummaryData` fixture.
    """
    return _DEFAULT_TEST_DATA_BUILDER.build_sample_summary()


def build_cli_summary() -> SummaryData:
    """Build a `SummaryData` fixture for CLI formatting and helper tests.

    This is the preferred entry point for tests that exercise CLI-facing summary
    traversal and formatting logic. The returned payload is intentionally minimal
    while remaining structurally valid and stable:

    - Ensures required keys exist (`generatedAt`, `projectRoot`, `tabs`, etc.).
    - Populates commonly-consumed tabs (overview/hotspots/readiness/runs/engines).
    - Uses deterministic values to keep assertions and snapshots reliable.

    Returns:
        A deterministic, structurally valid `SummaryData` fixture for CLI tests.
    """
    return _DEFAULT_TEST_DATA_BUILDER.build_cli_summary()


def build_cli_run_result() -> RunResult:
    """Build a `RunResult` fixture for CLI run output tests.

    This is the preferred entry point for tests that validate rendering and formatting
    of a single run, including diagnostic listing and run metadata presentation.
    The returned run is deterministic and includes at least one diagnostic.

    Returns:
        A deterministic `RunResult` fixture seeded with representative diagnostics.
    """
    return _DEFAULT_TEST_DATA_BUILDER.build_cli_run_result()


def build_readiness_entries(count: int = 200) -> list[ReadinessEntry]:
    """Build readiness entries for readiness scoring and bucketing tests.

    This wrapper provides a stable dataset with deterministic variation across entries,
    suitable for benchmarking and validating readiness computations.

    Args:
        count: Number of readiness entries to generate.

    Returns:
        A list of synthetic readiness entries.
    """
    return _DEFAULT_TEST_DATA_BUILDER.build_readiness_entries(count)


def build_sample_run(num_files: int = 120, diagnostics_per_file: int = 5) -> RunResult:
    """Build a `RunResult` fixture for performance and summarization tests.

    This wrapper is the preferred entry point for tests that benchmark or stress
    summarization/aggregation code paths by generating a large number of diagnostics.

    Args:
        num_files: Number of distinct file paths represented in the run.
        diagnostics_per_file: Number of diagnostics to generate per file.

    Returns:
        A `RunResult` containing synthetic diagnostics for performance-oriented tests.
    """
    return _DEFAULT_TEST_DATA_BUILDER.build_sample_run(num_files, diagnostics_per_file)


def build_cli_manifest(tmp_path: Path) -> Path:
    """Generate a representative CLI manifest JSON file for integration tests.

    The manifest includes multiple runs and representative nested structures
    (per-folder/per-file summaries, engine options, and diagnostics). It is intended
    for tests that validate manifest loading, schema compatibility, and CLI workflows
    that operate over persisted artifacts.

    Args:
        tmp_path: Temporary directory into which the manifest file is written.

    Returns:
        Path to the generated manifest JSON file.
    """
    manifest: dict[str, Any] = {
        "generatedAt": "2025-11-05T00:00:00Z",
        "projectRoot": str(tmp_path),
        "schemaVersion": CURRENT_MANIFEST_VERSION,
        "runs": [
            {
                "tool": "pyright",
                "mode": "current",
                "command": ["pyright", "--project"],
                "exitCode": 1,
                "durationMs": 12,
                "summary": {
                    "errors": 4,
                    "warnings": 2,
                    "information": 0,
                    "total": 6,
                    "severityBreakdown": {"error": 4, "warning": 2},
                    "ruleCounts": {"reportGeneralTypeIssues": 4},
                    "categoryCounts": {"unknownChecks": 4},
                },
                "engineOptions": {
                    "profile": "strict",
                    "configFile": "pyrightconfig.json",
                    "pluginArgs": ["--strict"],
                    "include": [RelPath("src")],
                    "exclude": [RelPath("tests")],
                    "overrides": [{"path": "src", "profile": "strict"}],
                    "categoryMapping": {"unknownChecks": ["reportGeneralTypeIssues"]},
                },
                "perFolder": [
                    {
                        "path": "src",
                        "depth": 1,
                        "errors": 3,
                        "warnings": 2,
                        "information": 0,
                        "codeCounts": {"reportGeneralTypeIssues": 4},
                        "categoryCounts": {"unknownChecks": 4},
                        "recommendations": ["add type annotations"],
                    },
                ],
                "perFile": [
                    {
                        "path": "src/app.py",
                        "errors": 3,
                        "warnings": 0,
                        "information": 0,
                        "diagnostics": [
                            {
                                "line": 10,
                                "column": 4,
                                "severity": "error",
                                "code": "reportGeneralTypeIssues",
                                "message": "strict mode failure",
                            },
                        ],
                    },
                    {
                        "path": "src/utils.py",
                        "errors": 0,
                        "warnings": 2,
                        "information": 0,
                        "diagnostics": [
                            {
                                "line": 20,
                                "column": 2,
                                "severity": "warning",
                                "code": "reportUnknownVariableType",
                                "message": "graduated warning",
                            },
                        ],
                    },
                ],
            },
            {
                "tool": "mypy",
                "mode": "target",
                "command": ["mypy", "--strict"],
                "exitCode": 0,
                "durationMs": 15,
                "summary": {
                    "errors": 0,
                    "warnings": 1,
                    "information": 1,
                    "total": 2,
                    "severityBreakdown": {"warning": 1, "information": 1},
                    "ruleCounts": {"attr-defined": 1},
                    "categoryCounts": {"general": 1},
                },
                "engineOptions": {
                    "profile": "baseline",
                    "configFile": "mypy.ini",
                    "pluginArgs": [],
                    "include": [RelPath("src")],
                    "exclude": [],
                    "overrides": [],
                    "categoryMapping": {},
                },
                "perFolder": [
                    {
                        "path": "src",
                        "depth": 1,
                        "errors": 0,
                        "warnings": 1,
                        "information": 1,
                        "codeCounts": {"attr-defined": 1},
                        "categoryCounts": {"general": 1},
                        "recommendations": [],
                    },
                ],
                "perFile": [
                    {
                        "path": "src/app.py",
                        "errors": 0,
                        "warnings": 1,
                        "information": 1,
                        "diagnostics": [
                            {
                                "line": 30,
                                "column": 6,
                                "severity": "warning",
                                "code": "attr-defined",
                                "message": "attr-defined warning",
                            },
                        ],
                    },
                ],
            },
        ],
    }
    manifest_path = tmp_path / "manifest.json"
    consume(manifest_path.write_text(json.dumps(manifest), encoding="utf-8"))
    return manifest_path
