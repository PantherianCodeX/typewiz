# Copyright (c) 2024 PantherianCodeX

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("pytest_benchmark")

from typewiz.aggregate import summarise_run
from typewiz.model_types import Mode
from typewiz.readiness import ReadinessEntry, compute_readiness
from typewiz.types import Diagnostic, RunResult


def _build_readiness_entries(count: int = 200) -> list[ReadinessEntry]:
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


def _build_sample_run(num_files: int = 120, diagnostics_per_file: int = 5) -> RunResult:
    diagnostics: list[Diagnostic] = []
    for file_index in range(num_files):
        path = Path(f"pkg/module_{file_index}.py")
        diagnostics.extend(
            Diagnostic(
                tool="pyright",
                severity="error" if diag_index % 3 == 0 else "warning",
                path=path,
                line=diag_index + 1,
                column=1,
                code=f"reportUnknown{diag_index % 4}",
                message="example diagnostic",
            )
            for diag_index in range(diagnostics_per_file)
        )
    return RunResult(
        tool="pyright",
        mode=Mode.CURRENT,
        command=["pyright"],
        exit_code=0,
        duration_ms=0.0,
        diagnostics=diagnostics,
        category_mapping={"unknownChecks": ["reportunknown"], "optionalChecks": ["optional"]},
    )


READINESS_SAMPLE: list[ReadinessEntry] = _build_readiness_entries()
RUN_SAMPLE: RunResult = _build_sample_run()


def test_compute_readiness_benchmark(benchmark: Any) -> None:
    benchmark(lambda: compute_readiness(READINESS_SAMPLE))


def test_summarise_run_benchmark(benchmark: Any) -> None:
    benchmark(lambda: summarise_run(RUN_SAMPLE, max_depth=4))
