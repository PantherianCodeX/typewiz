# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Performance tests for Benchmarks Core Operations."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

import pytest

from tests.fixtures.builders import TestDataBuilder
from typewiz.manifest.aggregate import summarise_run
from typewiz.readiness.compute import ReadinessEntry, compute_readiness

pytestmark = [pytest.mark.benchmark, pytest.mark.slow]

pytest.importorskip("pytest_benchmark")


class BenchmarkRunner(Protocol):
    def __call__(self, func: Callable[[], object], /, *args: object, **kwargs: object) -> object:
        """Callable interface exposed by pytest-benchmark fixtures."""


_TEST_DATA_BUILDER = TestDataBuilder()
READINESS_SAMPLE: list[ReadinessEntry] = _TEST_DATA_BUILDER.build_readiness_entries()
RUN_SAMPLE = _TEST_DATA_BUILDER.build_sample_run()


def test_compute_readiness_benchmark(benchmark: BenchmarkRunner) -> None:
    benchmark(lambda: compute_readiness(READINESS_SAMPLE))


def test_summarise_run_benchmark(benchmark: BenchmarkRunner) -> None:
    benchmark(lambda: summarise_run(RUN_SAMPLE, max_depth=4))
