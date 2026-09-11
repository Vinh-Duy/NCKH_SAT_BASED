"""Order-encoded CNF model for L(h,k)-labeling."""


class OrderVars:
    """Map each vertex and threshold to a positive SAT variable."""

    def __init__(self, n_vertices: int, span: int):
        self.n_vertices = n_vertices
        self.span = span
        self.next_var = 1
        self.x = {
            vertex: {
                threshold: self._allocate()
                for threshold in range(span)
            }
            for vertex in range(n_vertices)
        }

    def _allocate(self) -> int:
        variable = self.next_var
        self.next_var += 1
        return variable

    def leq(self, vertex: int, threshold: int) -> int | None:
        """Return x(vertex, threshold), or a constant boundary marker."""
        if threshold < 0 or threshold >= self.span:
            return None
        return self.x[vertex][threshold]

    @property
    def variable_count(self) -> int:
        return self.next_var - 1


def monotone_clauses(order_vars: OrderVars) -> list[list[int]]:
    """Enforce x(v,i) implies x(v,i+1)."""
    return [
        [-order_vars.x[vertex][threshold], order_vars.x[vertex][threshold + 1]]
        for vertex in range(order_vars.n_vertices)
        for threshold in range(order_vars.span - 1)
    ]


def not_equal_literals(order_vars: OrderVars, vertex: int, label: int) -> list[int]:
    """Return literals for the negation of f(vertex) == label."""
    literals = []
    at_label = order_vars.leq(vertex, label)
    below_label = order_vars.leq(vertex, label - 1)
    if at_label is not None:
        literals.append(-at_label)
    if below_label is not None:
        literals.append(below_label)
    return literals


def forbid_close_labels(
    order_vars: OrderVars, first: int, second: int, minimum_difference: int
) -> list[list[int]]:
    """Forbid every label pair closer than minimum_difference."""
    clauses = []
    for first_label in range(order_vars.span + 1):
        lower = max(0, first_label - minimum_difference + 1)
        upper = min(order_vars.span, first_label + minimum_difference - 1)
        for second_label in range(lower, upper + 1):
            clauses.append(
                not_equal_literals(order_vars, first, first_label)
                + not_equal_literals(order_vars, second, second_label)
            )
    return clauses if minimum_difference > 0 else []


def strict_less_clauses(
    order_vars: OrderVars, smaller: int, larger: int
) -> list[list[int]]:
    """Encode f(smaller) < f(larger) in order encoding."""
    if order_vars.span == 0:
        return [[]]
    clauses = [[order_vars.x[smaller][order_vars.span - 1]]]
    clauses.extend(
        [-order_vars.x[larger][threshold], order_vars.x[smaller][threshold - 1]]
        for threshold in range(1, order_vars.span)
    )
    clauses.append([-order_vars.x[larger][0]])
    return clauses


def symmetry_breaking_clauses(
    order_vars: OrderVars, symmetry_kind: str | None
) -> list[list[int]]:
    """Add sound symmetry constraints for supported graph families."""
    if not symmetry_kind or order_vars.n_vertices == 0:
        return []
    builders = {
        "P": _path_symmetry,
        "C": _cycle_symmetry,
        "K": _complete_symmetry,
        "Q": _hypercube_symmetry,
    }
    builder = builders.get(symmetry_kind)
    return builder(order_vars) if builder else []


def _fixed_zero_clause(order_vars: OrderVars) -> list[list[int]]:
    if order_vars.span > 0:
        return [[order_vars.x[0][0]]]
    return []


def _path_symmetry(order_vars: OrderVars) -> list[list[int]]:
    if order_vars.n_vertices < 2:
        return []
    return strict_less_clauses(order_vars, 0, order_vars.n_vertices - 1)


def _cycle_symmetry(order_vars: OrderVars) -> list[list[int]]:
    if order_vars.n_vertices < 3:
        return []
    return _fixed_zero_clause(order_vars) + strict_less_clauses(
        order_vars, 1, order_vars.n_vertices - 1
    )


def _complete_symmetry(order_vars: OrderVars) -> list[list[int]]:
    if order_vars.n_vertices < 2:
        return []
    clauses = _fixed_zero_clause(order_vars)
    for vertex in range(order_vars.n_vertices - 1):
        clauses += strict_less_clauses(order_vars, vertex, vertex + 1)
    return clauses


def _hypercube_symmetry(order_vars: OrderVars) -> list[list[int]]:
    dimension = order_vars.n_vertices.bit_length() - 1
    if dimension < 1 or 2**dimension != order_vars.n_vertices:
        return []
    clauses = _fixed_zero_clause(order_vars)
    for bit in range(1, dimension):
        clauses += strict_less_clauses(
            order_vars, 1 << (bit - 1), 1 << bit
        )
    return clauses


def build_cnf(
    n_vertices: int,
    edges: list[tuple[int, int]],
    distance_two_pairs: list[tuple[int, int]],
    span: int,
    h: int = 2,
    k: int = 1,
    symmetry_kind: str | None = None,
) -> tuple[list[list[int]] | None, OrderVars]:
    """Build an L(h,k) CNF and return it with its order variables."""
    order_vars = OrderVars(n_vertices, span)
    clauses = monotone_clauses(order_vars)
    clauses += symmetry_breaking_clauses(order_vars, symmetry_kind)
    for first, second in edges:
        clauses += forbid_close_labels(order_vars, first, second, h)
    for first, second in distance_two_pairs:
        clauses += forbid_close_labels(order_vars, first, second, k)
    if any(not clause for clause in clauses):
        return None, order_vars
    return clauses, order_vars
