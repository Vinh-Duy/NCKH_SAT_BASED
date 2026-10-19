"""An alternative order encoding with one orientation per separated pair.

The order variables retain the convention ``x[v,t] <=> f(v) <= t``.
For a gap g>0, an auxiliary variable selects f(u)+g<=f(v) or its
reverse.  Each orientation consists of two endpoint bounds and the
implications x[v,t] => x[u,t-g], g<=t<span.  Thus a pair contributes
2*(span-g+2) clauses rather than enumerating forbidden label pairs.

This module is experimental and does not change the benchmark solver.
The optional symmetries preserve existence of a labeling, not every
individual assignment.  No graph vertex is fixed to zero.
"""

from src.core.parameters import validate_gaps
from src.models.sat_encoding import (
    OrderVars, forbid_close_labels, monotone_clauses, simplify_cnf,
)


def oriented_separation_clauses(order_vars, first, second, gap, selector):
    """Encode selector => f(first)+gap<=f(second), for 0<gap<=span.

    Necessity follows directly from the inequality.  For sufficiency,
    the endpoint bounds cover f(second)=span and values below gap;
    otherwise the implication at t=f(second) gives the inequality.
    A negative selector literal selects the reverse branch when used
    in the companion call.
    """
    span = order_vars.span
    if not 0 < gap <= span:
        raise ValueError("oriented separation requires 0 < gap <= span")
    x = order_vars.x
    clauses = [
        [-selector, -x[second][gap - 1]],
        [-selector, x[first][span - gap]],
    ]
    clauses.extend(
        [-selector, -x[second][threshold], x[first][threshold - gap]]
        for threshold in range(gap, span)
    )
    return clauses


def build_separation_cnf(
    n_vertices, edges, distance_two_pairs, span, h=2, k=1, *,
    normalize=False, reflection_root=None, equality_pairwise=True,
    simplify=True,
):
    """Build a bounded-span formula equivalent to L(h,k) feasibility.

    ``equality_pairwise`` retains the smaller forbidden-equality clauses
    for gap one; all larger gaps use orientation variables.  A positive
    gap exceeding the domain width yields immediate infeasibility.

    ``normalize`` requires some vertex to receive zero.  ``reflection_root``
    restricts one chosen vertex to the lower half of the domain.  Together
    these remain sound: subtract the minimum label, then if necessary
    reflect every label about the *actual* maximum, which is at most span.
    Neither restriction relies on vertex transitivity or graph automorphisms.
    """
    validate_gaps(h, k)
    for name, value in (("n_vertices", n_vertices), ("span", span)):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{name} must be a non-negative integer")
    if reflection_root is not None and (
        isinstance(reflection_root, bool)
        or not isinstance(reflection_root, int)
        or reflection_root not in range(n_vertices)
    ):
        raise ValueError("reflection_root must be a vertex index")
    order_vars = OrderVars(n_vertices, span)
    clauses = monotone_clauses(order_vars)
    if normalize and n_vertices and span:
        clauses.append([order_vars.x[v][0] for v in range(n_vertices)])
    if reflection_root is not None and span:
        clauses.append([order_vars.x[reflection_root][span // 2]])
    for pairs, gap in ((edges, h), (distance_two_pairs, k)):
        for first, second in pairs:
            if any(isinstance(v, bool) or not isinstance(v, int)
                   or v not in range(n_vertices) for v in (first, second)):
                raise ValueError("constraint endpoints must be vertex indices")
            if first == second:
                raise ValueError("constraint endpoints must be distinct")
            if gap == 0:
                continue
            if gap > span:
                clauses.append([])
                continue
            if gap == 1 and equality_pairwise:
                clauses.extend(forbid_close_labels(order_vars, first, second, gap))
            else:
                selector = order_vars._allocate()
                clauses.extend(oriented_separation_clauses(
                    order_vars, first, second, gap, selector))
                clauses.extend(oriented_separation_clauses(
                    order_vars, second, first, gap, -selector))
    order_vars.raw_clause_count = len(clauses)
    if simplify:
        clauses = simplify_cnf(clauses)
    if any(not clause for clause in clauses):
        return None, order_vars
    return clauses, order_vars
