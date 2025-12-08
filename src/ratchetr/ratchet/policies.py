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

"""Signature policy utilities for ratchet comparisons."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ratchetr.core.model_types import SignaturePolicy

if TYPE_CHECKING:
    from collections.abc import Mapping

    from ratchetr.json import JSONValue


@dataclass(slots=True)
class SignatureCheck:
    """Result of comparing engine signatures with policy enforcement.

    Attributes:
        matches (bool): Whether the expected and actual signatures match.
        policy (SignaturePolicy): The policy to apply when signatures don't match.
    """

    matches: bool
    policy: SignaturePolicy

    def should_fail(self) -> bool:
        """Check if the signature mismatch should cause a failure.

        Returns:
            bool: True if signatures don't match and policy is FAIL.
        """
        return not self.matches and self.policy is SignaturePolicy.FAIL

    def should_warn(self) -> bool:
        """Check if the signature mismatch should generate a warning.

        Returns:
            bool: True if signatures don't match and policy is WARN.
        """
        return not self.matches and self.policy is SignaturePolicy.WARN


def compare_signatures(
    expected: Mapping[str, JSONValue] | None,
    actual: Mapping[str, JSONValue] | None,
    policy: SignaturePolicy,
) -> SignatureCheck:
    """Compare expected and actual engine signatures.

    Args:
        expected (Mapping[str, JSONValue] | None): The expected engine signature containing a hash.
        actual (Mapping[str, JSONValue] | None): The actual engine signature containing a hash.
        policy (SignaturePolicy): The policy for handling signature mismatches.

    Returns:
        SignatureCheck: A check result indicating whether signatures match and the enforcement policy.
    """
    expected_hash = (expected or {}).get("hash")
    actual_hash = (actual or {}).get("hash")
    matches = expected_hash == actual_hash
    return SignatureCheck(matches=matches, policy=policy)


__all__ = [
    "SignatureCheck",
    "SignaturePolicy",
    "compare_signatures",
]
