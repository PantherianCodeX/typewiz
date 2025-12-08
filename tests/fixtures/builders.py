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
from typing import TYPE_CHECKING, Any, Final

from ratchetr._internal.utils import consume
from ratchetr.core.model_types import Mode, OverrideEntry, ReadinessStatus, SeverityLevel
from ratchetr.core.summary_types import (
    CountsByCategory,
    CountsByRule,
    CountsBySeverity,
    EnginesTab,
    HotspotsTab,
    OverviewTab,
    ReadinessOptionEntry,
    ReadinessOptionsPayload,
    ReadinessStrictEntry,
    ReadinessTab,
    RulePathEntry,
    RunsTab,
    SummaryData,
    SummaryFileEntry,
    SummaryFolderEntry,
    SummaryRunEntry,
    SummaryTabs,
)
from ratchetr.core.type_aliases import CategoryKey, CategoryName, RelPath, RunId, ToolName
from ratchetr.core.types import Diagnostic, RunResult
from ratchetr.manifest.versioning import CURRENT_MANIFEST_VERSION

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

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

TOOL_PYRIGHT: Final[ToolName] = ToolName("pyright")
TOOL_STUB: Final[ToolName] = ToolName("stub")


@dataclass(slots=True)
class TestDataBuilder:
    """Factory for rich sample payloads used in tests."""

    __test__ = False

    project_root: Path = Path("/repo")
    generated_at: str = "2025-01-01T00:00:00Z"
    tool_name: ToolName = TOOL_PYRIGHT
    stub_tool_name: ToolName = TOOL_STUB

    def build_sample_summary(self) -> SummaryData:
        """Return a representative SummaryData payload used by dashboard tests."""
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
            Mapping from ``RunId`` to synthetic ``SummaryRunEntry`` payloads
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
            RunId("mypy:full"): {
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
            ``ReadinessTab`` payload containing strict and per-option
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
    def _build_sample_tabs(  # noqa: PLR0913  # JUSTIFIED: test data builder requires explicit, keyword-only inputs for readability across many callers
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
            Complete ``SummaryTabs`` mapping for use in CLI and dashboard
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
        """Return dashboard summary tailored to CLI helper tests."""
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
        """Build a RunResult tailored to CLI printing tests.

        Returns:
            ``RunResult`` seeded with representative diagnostics and metadata.
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
        """Generate readiness entries that stress readiness computation.

        Args:
            count: Number of readiness records to emit.

        Returns:
            List of synthetic readiness entries.
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
        """Construct a run with many diagnostics for performance testing.

        Args:
            num_files: Number of files represented in the run.
            diagnostics_per_file: Diagnostics to generate per file.
            tool_name: Optional override for the tool identifier.

        Returns:
            ``RunResult`` packed with synthetic diagnostics.
        """
        diagnostics: list[Diagnostic] = []
        target_tool = tool_name or self.tool_name
        for file_index in range(num_files):
            path = Path(f"pkg/module_{file_index}.py")
            diagnostics.extend(
                Diagnostic(
                    tool=target_tool,
                    severity=(SeverityLevel.ERROR if diag_index % 3 == 0 else SeverityLevel.WARNING),
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
DEFAULT_READINESS_CATEGORY: CategoryKey = "unknownChecks"


def build_sample_summary() -> SummaryData:
    """Convenience wrapper for the default sample summary.

    Returns:
        Sample ``SummaryData`` used by CLI tests.
    """
    return _DEFAULT_TEST_DATA_BUILDER.build_sample_summary()


def build_cli_summary() -> SummaryData:
    """Return the CLI helper sample summary."""
    return _DEFAULT_TEST_DATA_BUILDER.build_cli_summary()


def build_cli_run_result() -> RunResult:
    """Return a representative RunResult for CLI helper tests."""
    return _DEFAULT_TEST_DATA_BUILDER.build_cli_run_result()


def build_readiness_entries(count: int = 200) -> list[ReadinessEntry]:
    """Return readiness entries for benchmarking tests."""
    return _DEFAULT_TEST_DATA_BUILDER.build_readiness_entries(count)


def build_sample_run(num_files: int = 120, diagnostics_per_file: int = 5) -> RunResult:
    """Return a RunResult suitable for benchmarking summarise_run."""
    return _DEFAULT_TEST_DATA_BUILDER.build_sample_run(num_files, diagnostics_per_file)


def build_cli_manifest(tmp_path: Path) -> Path:
    """Generate a representative CLI manifest for integration tests.

    Args:
        tmp_path: Temporary directory used to write the manifest file.

    Returns:
        Path to the generated manifest file.
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
                "mode": "full",
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


def build_empty_summary() -> SummaryData:
    """Construct a blank SummaryData payload with the required structure.

    Returns:
        ``SummaryData`` skeleton with empty tabs.
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
    """Return a Diagnostic populated with sensible defaults for CLI-oriented tests."""
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


def build_readiness_summary(
    *,
    option_entries: Mapping[ReadinessStatus, Sequence[ReadinessOptionEntry]] | None = None,
    strict_entries: Mapping[ReadinessStatus, Sequence[ReadinessStrictEntry]] | None = None,
    category: CategoryKey = DEFAULT_READINESS_CATEGORY,
    threshold: int = 0,
) -> SummaryData:
    """Return SummaryData populated with the supplied readiness entries."""
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
