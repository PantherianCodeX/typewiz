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

# ignore JUSTIFIED: File contains purposely bad code for demonstation purposes
# pragma: no cover  # type: ignore  # ruff: noqa: PGH003  # pylint: skip-file

"""Demonstration of typing issues that pyright can detect."""

from typing import Optional


# ignore JUSTIFIED: demo omits a None guard so pyright can report unsafe access while
# Ruff tolerates this pattern
def process_optional(value: Optional[str]) -> int:  # noqa: UP045
    return len(value)  # Should check if value is None first


# ignore JUSTIFIED: demo uses implicit Any so pyright can report missing parameter
# types
def implicit_any(data):  # noqa: ANN001, ANN201
    return data.get("key")  # Unknown attribute access


# ignore JUSTIFIED: demo omits type narrowing so pyright can report invalid attribute
# access on a union
def type_narrowing_demo(value: str | int) -> str:
    return value.upper()  # Error: 'int' has no attribute 'upper'


class DataProcessor:
    # ignore JUSTIFIED: demo uses an overly general dict type so pyright can report
    # configuration shape issues
    def __init__(self, config: dict):  # noqa: ANN204
        self.config = config

    # ignore JUSTIFIED: demo omits a return annotation so pyright can report incomplete
    # method typing
    def get_setting(self, key: str):  # noqa: ANN201
        return self.config.get(key, "default")


# Intentional: match statement omits the None case so pyright reports incomplete
# pattern coverage
def incomplete_match(value: str | int | None) -> str:
    match value:
        case str():
            return value
        case int():
            return str(value)
        # Missing None case - pyright will flag incomplete pattern


if __name__ == "__main__":
    # ignore JUSTIFIED: demo uses print statements to show runtime behaviour; T201 is
    # suppressed only in this example module
    print(process_optional("test"))  # noqa: T201
    # ignore JUSTIFIED: demo uses print statements to show runtime behaviour; T201 is
    # suppressed only in this example module
    print(implicit_any({"key": "value"}))  # noqa: T201
