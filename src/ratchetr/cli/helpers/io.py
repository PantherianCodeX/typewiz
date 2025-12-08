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

"""IO helpers for CLI output."""

from __future__ import annotations

import sys
from typing import Protocol

from ratchetr.runtime import consume


class _TextStream(Protocol):
    def write(self, s: str, /) -> int: ...


def _select_stream(*, err: bool = False) -> _TextStream:
    return sys.stderr if err else sys.stdout


def echo(message: str, *, newline: bool = True, err: bool = False) -> None:
    """Write a message to stdout/stderr, mirroring legacy CLI behaviour."""
    stream = _select_stream(err=err)
    consume(stream.write(message))
    if newline:
        consume(stream.write("\n"))


__all__ = ["echo"]
