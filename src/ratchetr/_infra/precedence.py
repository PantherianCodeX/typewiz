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

"""Generic precedence chain resolution for ratchetr settings.

This module provides a reusable implementation of ratchetr's standard
precedence chain: CLI > environment > config > default.
"""

from __future__ import annotations

from typing import TypeVar

T = TypeVar("T")


def resolve_with_precedence(
    *,
    cli_value: T | None = None,
    env_value: T | None = None,
    config_value: T | None = None,
    default: T,
) -> T:
    """Resolve a value using ratchetr's standard precedence chain.

    Precedence (highest to lowest):
    1. CLI argument/flag
    2. Environment variable
    3. Config file setting
    4. Default value

    Args:
        cli_value: Value from CLI argument.
        env_value: Value from environment variable.
        config_value: Value from config file.
        default: Fallback default value.

    Returns:
        The highest-precedence non-None value, or default.

    Example:
        >>> resolve_with_precedence(
        ...     cli_value=["src"], env_value=["lib"], config_value=["pkg"], default=["."]
        ... )
        ['src']
        >>> resolve_with_precedence(
        ...     cli_value=None, env_value=["lib"], config_value=["pkg"], default=["."]
        ... )
        ['lib']
    """
    if cli_value is not None:
        return cli_value
    if env_value is not None:
        return env_value
    if config_value is not None:
        return config_value
    return default
