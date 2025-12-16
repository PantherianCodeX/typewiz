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
# pragma: no cover  # type: ignore  # pylint: skip-file

"""Demonstration of typing issues that mypy can detect."""


# Intentional: demo leaves this function untyped so mypy can report missing
# annotations while Ruff tolerates the pattern (but catches all others in this demo).
def greet(name):
    return f"Hello, {name}!"


# Intentional: demo uses the wrong return type to showcase mypy's
# return-type mismatch diagnostics
def add_numbers(x: int, y: int) -> str:
    return x + y  # Returns int, not str


def process_data(items: list) -> int:
    return len(items)


# Intentional: class with incomplete typing so mypy reports missing
# annotations;
class Calculator:
    # Intentional: constructor parameter stays untyped so mypy can report missing
    # annotations
    def __init__(self, initial_value):
        self.value = initial_value

    # Intentional: method omits a return annotation so mypy can report incomplete
    # method typing
    def add(self, amount: int):
        self.value += amount
        return self.value


if __name__ == "__main__":
    # Intentional: demo uses print statements to show runtime behaviour; T201 is
    # suppressed only in this example module
    print(greet("World"))
    # Intentional: demo uses print statements to show runtime behaviour; T201 is
    # suppressed only in this example module
    print(add_numbers(5, 3))
