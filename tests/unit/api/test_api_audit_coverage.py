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

"""Comprehensive tests for audit/api.py - properly testing actual functionality."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest import mock

import pytest

from ratchetr import AuditConfig, Config, run_audit
from ratchetr.audit.api import (
    AuditResult,
    _compute_run_totals,
    _determine_default_include,
    _iterate_modes,
    _prepare_audit_inputs,
)
from ratchetr.core.model_types import Mode, SeverityLevel
from ratchetr.core.type_aliases import ToolName
from ratchetr.core.types import Diagnostic, RunResult

if TYPE_CHECKING:
    from pathlib import Path

    from ratchetr.manifest.typed import ManifestData

pytestmark = pytest.mark.unit

STUB_TOOL = ToolName("stub")


class TestIterateModes:
    """Test _iterate_modes function."""

    @staticmethod
    def test_iterate_modes_both_enabled() -> None:
        """Both CURRENT and TARGET should be included when neither is skipped."""
        config = AuditConfig()
        modes = _iterate_modes(config)
        assert modes == [Mode.CURRENT, Mode.TARGET]

    @staticmethod
    def test_iterate_modes_skip_current() -> None:
        """Only TARGET when CURRENT is skipped."""
        config = AuditConfig(skip_current=True)
        modes = _iterate_modes(config)
        assert modes == [Mode.TARGET]

    @staticmethod
    def test_iterate_modes_skip_target() -> None:
        """Only CURRENT when TARGET is skipped."""
        config = AuditConfig(skip_target=True)
        modes = _iterate_modes(config)
        assert modes == [Mode.CURRENT]

    @staticmethod
    def test_iterate_modes_skip_both() -> None:
        """Empty list when both modes are skipped."""
        config = AuditConfig(skip_current=True, skip_target=True)
        modes = _iterate_modes(config)
        assert modes == []


class TestDetermineIncludePaths:
    """Test _determine_default_include function."""

    @staticmethod
    def test_default_include_explicit_override(tmp_path: Path) -> None:
        """Explicit default_include parameter takes precedence."""
        config = AuditConfig(default_include=["config_path"])
        explicit = ["explicit_path"]
        result = _determine_default_include(tmp_path, config, explicit)
        assert str(result[0]) == "explicit_path"

    @staticmethod
    def test_default_include_from_config(tmp_path: Path) -> None:
        """Config default_include used when no explicit override."""
        config = AuditConfig(default_include=["src", "tests"])
        result = _determine_default_include(tmp_path, config, None)
        assert len(result) == 2
        assert str(result[0]) == "src"
        assert str(result[1]) == "tests"

    @staticmethod
    def test_default_include_default_fallback(tmp_path: Path) -> None:
        """Default to ['.'] when config and explicit are both None/empty."""
        config = AuditConfig(default_include=None)
        result = _determine_default_include(tmp_path, config, None)
        assert len(result) == 1
        assert str(result[0]) == "."


class TestComputeRunTotals:
    """Test _compute_run_totals aggregation logic."""

    @staticmethod
    def test_compute_run_totals_empty_list_returns_zeros() -> None:
        """Empty run list should return zero counts."""
        error_count, warning_count = _compute_run_totals([])
        assert error_count == 0
        assert warning_count == 0

    @staticmethod
    def test_compute_run_totals_aggregates_across_runs(tmp_path: Path) -> None:
        """Should sum error/warning counts from all runs correctly."""
        (tmp_path / "test.py").touch()

        # Create three runs with different severity counts
        run1 = RunResult(
            tool=STUB_TOOL,
            mode=Mode.CURRENT,
            command=["tool"],
            exit_code=1,
            duration_ms=5.0,
            diagnostics=[
                Diagnostic(
                    tool=STUB_TOOL,
                    severity=SeverityLevel.ERROR,
                    path=tmp_path / "test.py",
                    line=1,
                    column=1,
                    code="E001",
                    message="Error 1",
                    raw={},
                ),
                Diagnostic(
                    tool=STUB_TOOL,
                    severity=SeverityLevel.ERROR,
                    path=tmp_path / "test.py",
                    line=2,
                    column=1,
                    code="E002",
                    message="Error 2",
                    raw={},
                ),
                Diagnostic(
                    tool=STUB_TOOL,
                    severity=SeverityLevel.WARNING,
                    path=tmp_path / "test.py",
                    line=3,
                    column=1,
                    code="W001",
                    message="Warning 1",
                    raw={},
                ),
            ],
        )

        run2 = RunResult(
            tool=STUB_TOOL,
            mode=Mode.TARGET,
            command=["tool"],
            exit_code=1,
            duration_ms=5.0,
            diagnostics=[
                Diagnostic(
                    tool=STUB_TOOL,
                    severity=SeverityLevel.ERROR,
                    path=tmp_path / "test.py",
                    line=4,
                    column=1,
                    code="E003",
                    message="Error 3",
                    raw={},
                ),
                Diagnostic(
                    tool=STUB_TOOL,
                    severity=SeverityLevel.WARNING,
                    path=tmp_path / "test.py",
                    line=5,
                    column=1,
                    code="W002",
                    message="Warning 2",
                    raw={},
                ),
                Diagnostic(
                    tool=STUB_TOOL,
                    severity=SeverityLevel.WARNING,
                    path=tmp_path / "test.py",
                    line=6,
                    column=1,
                    code="W003",
                    message="Warning 3",
                    raw={},
                ),
            ],
        )

        error_count, warning_count = _compute_run_totals([run1, run2])
        # run1 has 2 errors + 1 warning, run2 has 1 error + 2 warnings
        assert error_count == 3, f"Expected 3 errors, got {error_count}"
        assert warning_count == 3, f"Expected 3 warnings, got {warning_count}"

    @staticmethod
    def test_compute_run_totals_ignores_information_severity(tmp_path: Path) -> None:
        """Information severity messages should not be counted."""
        (tmp_path / "test.py").touch()

        run = RunResult(
            tool=STUB_TOOL,
            mode=Mode.CURRENT,
            command=["tool"],
            exit_code=0,
            duration_ms=5.0,
            diagnostics=[
                Diagnostic(
                    tool=STUB_TOOL,
                    severity=SeverityLevel.INFORMATION,
                    path=tmp_path / "test.py",
                    line=1,
                    column=1,
                    code="I001",
                    message="Information",
                    raw={},
                ),
                Diagnostic(
                    tool=STUB_TOOL,
                    severity=SeverityLevel.INFORMATION,
                    path=tmp_path / "test.py",
                    line=2,
                    column=1,
                    code="I002",
                    message="Information",
                    raw={},
                ),
            ],
        )

        error_count, warning_count = _compute_run_totals([run])
        assert error_count == 0
        assert warning_count == 0


class TestPrepareAuditInputs:
    """Test _prepare_audit_inputs function."""

    @staticmethod
    def test_prepare_audit_inputs_with_explicit_config(tmp_path: Path) -> None:
        """Returns inputs when explicit config provided."""
        config = Config(audit=AuditConfig(runners=["pyright"]))
        cfg, inputs = _prepare_audit_inputs(
            project_root=tmp_path,
            config=config,
            override=None,
            default_include=None,
        )
        assert inputs.root == tmp_path
        assert cfg.audit.runners == ["pyright"]

    @staticmethod
    def test_prepare_audit_inputs_with_override(tmp_path: Path) -> None:
        """Override config merges with loaded config."""
        base_config = Config(audit=AuditConfig(runners=["pyright"]))
        override_config = AuditConfig(runners=["mypy"])

        with mock.patch("ratchetr.audit.api.load_config", return_value=base_config):
            _, inputs = _prepare_audit_inputs(
                project_root=tmp_path,
                config=None,
                override=override_config,
                default_include=None,
            )
            # Override should be merged
            assert inputs.audit_config.runners == ["mypy"]

    @staticmethod
    def test_prepare_audit_inputs_explicit_default_include(tmp_path: Path) -> None:
        """Explicit default_include override config."""
        config = Config(audit=AuditConfig(runners=["pyright"]))
        _, inputs = _prepare_audit_inputs(
            project_root=tmp_path,
            config=config,
            override=None,
            default_include=["src", "tests"],
        )
        assert len(inputs.default_include_normalised) == 2


class TestRunAuditIntegration:
    """Integration tests for run_audit behavior."""

    @staticmethod
    def test_run_audit_respects_skip_modes(tmp_path: Path) -> None:
        """run_audit should return empty runs when both modes are skipped."""
        config = Config(
            audit=AuditConfig(
                runners=[],
                skip_current=True,
                skip_target=True,
            )
        )

        with (
            mock.patch("ratchetr.audit.api.resolve_engines", return_value=[]),
            mock.patch("ratchetr.audit.api._iterate_modes", return_value=[]),
        ):
            result = run_audit(
                project_root=tmp_path,
                config=config,
                build_summary_output=False,
            )
            assert isinstance(result, AuditResult)
            assert result.runs == []
            assert result.error_count == 0
            assert result.warning_count == 0

    @staticmethod
    def test_run_audit_includes_manifest_data(tmp_path: Path) -> None:
        """run_audit should always return manifest data."""
        config = Config(audit=AuditConfig(runners=[]))

        with mock.patch("ratchetr.audit.api.resolve_engines", return_value=[]):
            result = run_audit(
                project_root=tmp_path,
                config=config,
                build_summary_output=False,
            )

            # Manifest should always be present
            assert isinstance(result.manifest, dict)
            assert "generatedAt" in result.manifest
            assert "projectRoot" in result.manifest
            assert str(tmp_path) in result.manifest["projectRoot"]

    @staticmethod
    def test_run_audit_summary_optional_based_flag(tmp_path: Path) -> None:
        """run_audit summary generation should be controlled by flag."""
        config = Config(audit=AuditConfig(runners=[]))

        with mock.patch("ratchetr.audit.api.resolve_engines", return_value=[]):
            # With flag enabled
            result_with_summary = run_audit(
                project_root=tmp_path,
                config=config,
                build_summary_output=True,
            )
            assert result_with_summary.summary is not None
            assert isinstance(result_with_summary.summary, dict)

            # With flag disabled
            result_without_summary = run_audit(
                project_root=tmp_path,
                config=config,
                build_summary_output=False,
            )
            assert result_without_summary.summary is None


class TestAuditResultDataclass:
    """Test AuditResult dataclass structure and field handling."""

    @staticmethod
    def test_audit_result_stores_all_fields(tmp_path: Path) -> None:
        """AuditResult should properly store all provided fields."""
        manifest_data: ManifestData = {
            "generatedAt": "2025-01-01T00:00:00Z",
            "projectRoot": str(tmp_path),
            "schemaVersion": "1.0",
            "runs": [],
        }

        result = AuditResult(
            manifest=manifest_data,
            runs=[],
            summary=None,
            error_count=42,
            warning_count=17,
        )

        # Verify all fields are accessible
        assert result.manifest == manifest_data
        assert result.runs == []
        assert result.summary is None
        assert result.error_count == 42
        assert result.warning_count == 17

    @staticmethod
    def test_audit_result_with_summary_and_runs(tmp_path: Path) -> None:
        """AuditResult should properly handle runs and summary data together."""
        (tmp_path / "test.py").touch()

        manifest_data: ManifestData = {
            "generatedAt": "2025-01-01T00:00:00Z",
            "projectRoot": str(tmp_path),
            "schemaVersion": "1.0",
            "runs": [],
        }

        sample_run = RunResult(
            tool=STUB_TOOL,
            mode=Mode.CURRENT,
            command=["tool"],
            exit_code=1,
            duration_ms=5.0,
            diagnostics=[
                Diagnostic(
                    tool=STUB_TOOL,
                    severity=SeverityLevel.ERROR,
                    path=tmp_path / "test.py",
                    line=1,
                    column=1,
                    code="E001",
                    message="Error",
                    raw={},
                ),
            ],
        )

        sample_summary = {
            "generatedAt": "now",
            "projectRoot": str(tmp_path),
            "runSummary": {},
            "severityTotals": {SeverityLevel.ERROR: 1},
            "categoryTotals": {},
            "topRules": {},
            "topFolders": [],
            "topFiles": [],
            "ruleFiles": {},
            "tabs": {
                "overview": {"severityTotals": {}, "categoryTotals": {}, "runSummary": {}},
                "engines": {"runSummary": {}},
                "hotspots": {"topRules": {}, "topFolders": [], "topFiles": [], "ruleFiles": {}},
                "readiness": {"strict": {}, "options": {}},
                "runs": {"runSummary": {}},
            },
        }

        result = AuditResult(
            manifest=manifest_data,
            runs=[sample_run],
            summary=sample_summary,
            error_count=1,
            warning_count=0,
        )

        # Verify structure is intact
        assert len(result.runs) == 1
        assert result.runs[0].tool == STUB_TOOL
        assert result.error_count == 1
        assert result.warning_count == 0
        assert result.summary is not None
        assert "severityTotals" in result.summary
