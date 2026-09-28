"""Explicit reference labelings; never substituted for an experimental solver."""


def grid_l21_labeling(n: int, m: int) -> dict[int, int]:
    """Label row-major P_n square P_m by (2*i + 3*j) modulo 7.

    Gives span at most 6 for every positive n,m. Optimality for n,m>=4
    follows from the degree-four obstruction proved in the manuscript.
    """
    if any(not isinstance(x, int) or isinstance(x, bool) or x < 1 for x in (n, m)):
        raise ValueError("grid dimensions must be positive integers")
    return {i*m+j: (2*i+3*j) % 7 for i in range(n) for j in range(m)}
