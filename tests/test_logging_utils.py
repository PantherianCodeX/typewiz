# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

from __future__ import annotations

import json
import logging

from pytest import CaptureFixture

from typewiz._internal.logging_utils import configure_logging
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
