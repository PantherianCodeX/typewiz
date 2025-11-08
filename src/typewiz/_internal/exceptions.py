# Copyright (c) 2025 PantherianCodeX. All Rights Reserved.

"""Common exception hierarchy for Typewiz."""

from __future__ import annotations

__all__ = ["TypewizError", "TypewizTypeError", "TypewizValidationError"]


class TypewizError(Exception):
    """Base error for all Typewiz exceptions."""


class TypewizValidationError(TypewizError, ValueError):
    """Raised when input data fails validation checks."""


class TypewizTypeError(TypewizError, TypeError):
    """Raised when input data has an unexpected type."""
