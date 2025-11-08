# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

from __future__ import annotations

import json
import logging
from collections.abc import Generator

from pytest import CaptureFixture, fixture

from typewiz._internal.logging_utils import LOG_LEVELS, configure_logging
from typewiz.core.model_types import LogComponent, Mode


def test_configure_logging_json_emits_structured_logs(capsys: CaptureFixture[str]) -> None:
    configure_logging("json")
    logger = logging.getLogger("typewiz")
    logger.info(
        "hello",
        extra={
            "component": LogComponent.ENGINE,
            "tool": "pyright",
            "mode": Mode.CURRENT,
            "duration_ms": 1.2,
            "cached": False,
            "exit_code": 0,
        },
    )
    try:
        raise RuntimeError("boom")
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


def test_configure_logging_respects_level(capsys: CaptureFixture[str]) -> None:
    assert LOG_LEVELS == ("debug", "info", "warning", "error")
    configure_logging("text", log_level="warning")
    logger = logging.getLogger("typewiz")
    logger.info("ignored")
    logger.warning("recorded")
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "ignored" not in combined
    assert "recorded" in combined


@fixture(autouse=True)
def reset_typewiz_logging() -> Generator[None, None, None]:
    logger = logging.getLogger("typewiz")
    handlers = list(logger.handlers)
    level = logger.level
    propagate = logger.propagate
    yield
    logger.handlers.clear()
    logger.handlers.extend(handlers)
    logger.setLevel(level)
    logger.propagate = propagate
