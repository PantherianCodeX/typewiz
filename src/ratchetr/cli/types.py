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

"""Shared CLI type definitions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    import argparse

__all__ = ["SubparserCollection"]


class SubparserCollection(Protocol):
    """Protocol describing the subset of ``argparse._SubParsersAction`` we rely on.

    This protocol defines the minimal interface required for subparser registration
    in CLI command modules. It matches the signature of argparse's internal
    _SubParsersAction class without relying on private implementation details.
    """

    def add_parser(
        self,
        name: str,
        **kwargs: Any,  # noqa: ANN401  # JUSTIFIED: Protocol needs Any for kwargs to match argparse's _SubParsersAction signature with contravariance
    ) -> argparse.ArgumentParser:
        """Add a subparser to the collection.

        Args:
            name: Name of the subcommand.
            **kwargs: Keyword arguments forwarded to ArgumentParser (help, formatter_class, etc.).

        Returns:
            The created ArgumentParser for the subcommand.
        """
        ...  # pragma: no cover - Protocol definition
