from __future__ import annotations

from typewiz.core.model_types import ManifestAction, QuerySection, RatchetAction


def test_cli_enums_accept_case_insensitive_values() -> None:
    assert RatchetAction.from_str("INIT") is RatchetAction.INIT
    assert ManifestAction.from_str("Schema") is ManifestAction.SCHEMA
    assert QuerySection.from_str("Runs") is QuerySection.RUNS
