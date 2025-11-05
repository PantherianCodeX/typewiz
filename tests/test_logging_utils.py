from __future__ import annotations

import json
import logging

from pytest import CaptureFixture

from typewiz.logging_utils import configure_logging


def test_configure_logging_json_emits_structured_logs(capsys: CaptureFixture[str]) -> None:
    configure_logging("json")
    logger = logging.getLogger("typewiz")
    logger.info(
        "hello",
        extra={
            "component": "engine",
            "tool": "pyright",
            "mode": "current",
            "duration_ms": 1.2,
            "cached": False,
            "exit_code": 0,
        },
    )
    captured = capsys.readouterr().err or capsys.readouterr().out
    # Handler prints a single JSON line
    line = captured.strip().splitlines()[-1]
    payload = json.loads(line)
    assert payload["message"] == "hello"
    assert payload["level"] == "info"
    assert payload["logger"] == "typewiz"
    assert payload["component"] == "engine"
    assert payload["tool"] == "pyright"
    assert payload["mode"] == "current"
    assert payload["duration_ms"] == 1.2
    assert payload["cached"] is False
    assert payload["exit_code"] == 0
