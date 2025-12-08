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

"""Performance tests for Benchmarks Core Operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

import pytest

from ratchetr.manifest.aggregate import summarise_run
from ratchetr.readiness.compute import ReadinessEntry, compute_readiness
from tests.fixtures.builders import TestDataBuilder

if TYPE_CHECKING:
    from collections.abc import Callable

pytestmark = [pytest.mark.benchmark, pytest.mark.slow]

pytest.importorskip("pytest_benchmark")


class BenchmarkRunner(Protocol):
    """Protocol for pytest-benchmark's ``benchmark`` fixture."""

    def __call__(self, func: Callable[[], object], /, *args: object, **kwargs: object) -> object:
        """Callable interface exposed by pytest-benchmark fixtures."""


_TEST_DATA_BUILDER = TestDataBuilder()
READINESS_SAMPLE: list[ReadinessEntry] = _TEST_DATA_BUILDER.build_readiness_entries()
RUN_SAMPLE = _TEST_DATA_BUILDER.build_sample_run()


def test_compute_readiness_benchmark(benchmark: BenchmarkRunner) -> None:
    benchmark(lambda: compute_readiness(READINESS_SAMPLE))


def test_summarise_run_benchmark(benchmark: BenchmarkRunner) -> None:
    benchmark(lambda: summarise_run(RUN_SAMPLE, max_depth=4))
