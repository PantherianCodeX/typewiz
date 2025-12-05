# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Unit tests for Utilities Logging."""

from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING

import pytest

from typewiz._internal.logging_utils import LOG_LEVELS, configure_logging, structured_extra
from typewiz.core.model_types import LogComponent, Mode, SeverityLevel

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

pytestmark = pytest.mark.unit


def test_configure_logging_json_emits_structured_logs(capsys: pytest.CaptureFixture[str]) -> None:
    _ = configure_logging("json")
    logger = logging.getLogger("typewiz")
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
    assert payload["logger"] == "typewiz"
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
    logger = logging.getLogger("typewiz")
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
    monkeypatch.setenv("TYPEWIZ_LOG_FORMAT", "json")
    monkeypatch.setenv("TYPEWIZ_LOG_LEVEL", "error")
    _ = configure_logging()
    logger = logging.getLogger("typewiz")
    logger.warning("warned")
    logger.error(
        "failed",
        extra=structured_extra(component=LogComponent.CLI, exit_code=1),
    )
    captured = capsys.readouterr()
    lines = [line for line in (captured.out + captured.err).splitlines() if line]
    assert json.loads(lines[-1])["message"] == "failed"
    assert all("warned" not in line for line in lines)


def test_structured_extra_normalises_inputs(tmp_path: Path) -> None:
    extra = structured_extra(
        component=LogComponent.CLI,
        tool="pyright",
        mode="current",
        counts={SeverityLevel.ERROR: 2},
        manifest=tmp_path / "typing_audit.json",
        run_id="pyright:current",
        details={"runs": 4},
    )
    assert "mode" in extra
    assert extra["mode"] is Mode.CURRENT
    assert "counts" in extra
    assert extra["counts"][SeverityLevel.ERROR] == 2
    assert "manifest" in extra
    assert extra["manifest"].endswith("typing_audit.json")
    assert "run_id" in extra
    assert extra["run_id"] == "pyright:current"
    assert "details" in extra
    assert extra["details"] == {"runs": 4}


@pytest.fixture(autouse=True)
def reset_typewiz_logging() -> Generator[None, None, None]:
    logger = logging.getLogger("typewiz")
    handlers = list(logger.handlers)
    level = logger.level
    propagate = logger.propagate
    env_log_format = os.environ.get("TYPEWIZ_LOG_FORMAT")
    env_log_level = os.environ.get("TYPEWIZ_LOG_LEVEL")
    yield
    logger.handlers.clear()
    logger.handlers.extend(handlers)
    logger.setLevel(level)
    logger.propagate = propagate
    if env_log_format is None:
        _ = os.environ.pop("TYPEWIZ_LOG_FORMAT", None)
    else:
        os.environ["TYPEWIZ_LOG_FORMAT"] = env_log_format
    if env_log_level is None:
        _ = os.environ.pop("TYPEWIZ_LOG_LEVEL", None)
    else:
        os.environ["TYPEWIZ_LOG_LEVEL"] = env_log_level
