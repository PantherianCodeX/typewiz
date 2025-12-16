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

"""Unit tests for Utilities Logging."""

from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING

import pytest

from ratchetr._infra.logging_utils import LOG_LEVELS, configure_logging, structured_extra
from ratchetr.core.model_types import LogComponent, Mode, SeverityLevel

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

pytestmark = pytest.mark.unit


def test_configure_logging_json_emits_structured_logs(capsys: pytest.CaptureFixture[str]) -> None:
    _ = configure_logging("json")
    logger = logging.getLogger("ratchetr")
    logger.info(
        "hello",
        extra=structured_extra(
            component=LogComponent.ENGINE,
            tool="pyright",
            mode=Mode.CURRENT,
            duration_ms=1.2,
            cached=False,
            exit_code=0,
        ),
    )

    def _raise_logging_failure() -> None:
        message = "boom"
        raise RuntimeError(message)

    try:
        _raise_logging_failure()
    except RuntimeError:
        logger.exception("broken")
    captured = capsys.readouterr()
    stream = captured.err or captured.out
    lines = [line for line in stream.strip().splitlines() if line]
    payload = json.loads(lines[-2])
    assert payload["message"] == "hello"
    assert payload["level"] == "info"
    assert payload["logger"] == "ratchetr"
    assert payload["component"] == "engine"
    assert payload["tool"] == "pyright"
    assert payload["mode"] == "current"
    assert payload["duration_ms"] == 1.2
    assert payload["cached"] is False
    assert payload["exit_code"] == 0

    exception_payload = json.loads(lines[-1])
    assert exception_payload["message"] == "broken"
    assert "exc_info" in exception_payload


def test_configure_logging_respects_level(capsys: pytest.CaptureFixture[str]) -> None:
    assert LOG_LEVELS == ("debug", "info", "warning", "error")
    _ = configure_logging("text", log_level="warning")
    logger = logging.getLogger("ratchetr")
    logger.info("ignored")
    logger.warning("recorded")
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "ignored" not in combined
    assert "recorded" in combined


def test_configure_logging_honors_env_overrides(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("RATCHETR_LOG_FORMAT", "json")
    monkeypatch.setenv("RATCHETR_LOG_LEVEL", "error")
    _ = configure_logging()
    logger = logging.getLogger("ratchetr")
    logger.warning("warned")
    logger.error(
        "failed",
        extra=structured_extra(component=LogComponent.CLI, exit_code=1),
    )
    captured = capsys.readouterr()
    lines = [line for line in (captured.out + captured.err).splitlines() if line]
    assert json.loads(lines[-1])["message"] == "failed"
    assert all("warned" not in line for line in lines)


def test_structured_extra_normalizes_inputs(tmp_path: Path) -> None:
    extra = structured_extra(
        component=LogComponent.CLI,
        tool="pyright",
        mode="current",
        counts={SeverityLevel.ERROR: 2},
        manifest=tmp_path / ".ratchetr/manifest",
        run_id="pyright:current",
        details={"runs": 4},
    )
    assert "mode" in extra
    assert extra["mode"] is Mode.CURRENT
    assert "counts" in extra
    assert extra["counts"][SeverityLevel.ERROR] == 2
    assert "manifest" in extra
    assert extra["manifest"].endswith(".ratchetr/manifest")
    assert "run_id" in extra
    assert extra["run_id"] == "pyright:current"
    assert "details" in extra
    assert extra["details"] == {"runs": 4}


@pytest.fixture(autouse=True)
def reset_ratchetr_logging() -> Generator[None, None, None]:
    logger = logging.getLogger("ratchetr")
    handlers = list(logger.handlers)
    level = logger.level
    propagate = logger.propagate
    env_log_format = os.environ.get("RATCHETR_LOG_FORMAT")
    env_log_level = os.environ.get("RATCHETR_LOG_LEVEL")
    yield
    logger.handlers.clear()
    logger.handlers.extend(handlers)
    logger.setLevel(level)
    logger.propagate = propagate
    if env_log_format is None:
        _ = os.environ.pop("RATCHETR_LOG_FORMAT", None)
    else:
        os.environ["RATCHETR_LOG_FORMAT"] = env_log_format
    if env_log_level is None:
        _ = os.environ.pop("RATCHETR_LOG_LEVEL", None)
    else:
        os.environ["RATCHETR_LOG_LEVEL"] = env_log_level
