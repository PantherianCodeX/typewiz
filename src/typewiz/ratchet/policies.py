# Copyright (c) 2024 PantherianCodeX
"""Signature policy utilities for ratchet comparisons."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from typewiz.runtime import JSONValue

from ..core.model_types import SignaturePolicy


@dataclass(slots=True)
class SignatureCheck:
    matches: bool
    policy: SignaturePolicy

    def should_fail(self) -> bool:
        return not self.matches and self.policy is SignaturePolicy.FAIL

    def should_warn(self) -> bool:
        return not self.matches and self.policy is SignaturePolicy.WARN


def compare_signatures(
    expected: Mapping[str, JSONValue] | None,
    actual: Mapping[str, JSONValue] | None,
    policy: SignaturePolicy,
) -> SignatureCheck:
    expected_hash = (expected or {}).get("hash")
    actual_hash = (actual or {}).get("hash")
    matches = expected_hash == actual_hash
    return SignatureCheck(matches=matches, policy=policy)


__all__ = [
    "SignaturePolicy",
    "SignatureCheck",
    "compare_signatures",
]
