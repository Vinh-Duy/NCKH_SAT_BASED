"""Shared domain for exact-distance L(h,k) models."""


def validate_gaps(h: int = 2, k: int = 1) -> None:
    """Accept non-negative integers; booleans and silent rounding are forbidden.

    The usual research regime h >= k >= 1 is a subset of this API domain.
    """
    for name, value in (("h", h), ("k", k)):
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"{name} must be a non-negative integer, got {value!r}")
