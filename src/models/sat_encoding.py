"""Order-encoded CNF model for L(h,k)-labeling."""

from collections import defaultdict, deque


def simplify_cnf(clauses: list[list[int]]) -> list[list[int]]:
    """Deduplicate and propagate units, retaining units for model reconstruction.

    The returned formula is logically equivalent over the original variables.
    This is the same preprocessing for baseline and symmetry configurations;
    it does not attempt to reproduce a SAT backend's internal preprocessing.
    """
    unique = set()
    residual = {}
    occurrences = defaultdict(set)
    queue = deque()
    for clause in clauses:
        literals = frozenset(clause)
        if not literals:
            return [[]]
        if any(-literal in literals for literal in literals) or literals in unique:
            continue
        unique.add(literals)
        index = len(residual)
        residual[index] = set(literals)
        for literal in literals:
            occurrences[literal].add(index)
        if len(literals) == 1:
            queue.append(next(iter(literals)))
    assigned = set()
    while queue:
        literal = queue.popleft()
        if -literal in assigned:
            return [[]]
        if literal in assigned:
            continue
        assigned.add(literal)
        for index in occurrences[literal]:
            residual.pop(index, None)
        for index in sorted(occurrences[-literal]):
            clause = residual.get(index)
            if clause is None:
                continue
            clause.discard(-literal)
            if not clause:
                return [[]]
            if len(clause) == 1:
                queue.append(next(iter(clause)))
    # Shortening may create duplicate clauses. Stable output keeps solver input
    # reproducible; propagated units must remain to constrain the decoder.
    shortened = dict.fromkeys(tuple(sorted(c)) for c in residual.values())
    return [[literal] for literal in sorted(assigned, key=abs)] + [
        list(clause) for clause in shortened
    ]


class OrderVars:
    """Map each vertex and threshold to a positive SAT variable."""

    def __init__(
        self,
        n_vertices: int,
        span: int,
        fixed_labels: dict[int, int] | None = None,
    ):
        if n_vertices < 0 or span < 0:
            raise ValueError("vertex count and span must be non-negative")
        if any(v not in range(n_vertices) or label not in range(span + 1)
               for v, label in (fixed_labels or {}).items()):
            raise ValueError("fixed labels must belong to the vertex and label domains")
        self.n_vertices = n_vertices
        self.span = span
        self.fixed_labels = fixed_labels or {}
        self.raw_clause_count = 0
        self.next_var = 1
        self.x = {
            vertex: {
                threshold: self._allocate()
                for threshold in range(span)
            }
            for vertex in range(n_vertices)
            if vertex not in self.fixed_labels
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
        for vertex in order_vars.x
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
    if minimum_difference <= 0:
        return []
    fixed_clauses = _fixed_close_label_clauses(
        order_vars, first, second, minimum_difference
    )
    if fixed_clauses is not None:
        return fixed_clauses

    return [
        not_equal_literals(order_vars, first, first_label)
        + not_equal_literals(order_vars, second, second_label)
        for first_label in range(order_vars.span + 1)
        for second_label in range(
            max(0, first_label - minimum_difference + 1),
            min(order_vars.span, first_label + minimum_difference - 1) + 1,
        )
    ]


def _fixed_close_label_clauses(
    order_vars: OrderVars,
    first: int,
    second: int,
    minimum_difference: int,
) -> list[list[int]] | None:
    first_fixed = order_vars.fixed_labels.get(first)
    second_fixed = order_vars.fixed_labels.get(second)
    if first_fixed is None and second_fixed is None:
        return None
    if first_fixed is not None and second_fixed is not None:
        return [[]] if abs(first_fixed - second_fixed) < minimum_difference else []
    fixed_label = first_fixed if first_fixed is not None else second_fixed
    free_vertex = second if first_fixed is not None else first
    return [
        not_equal_literals(order_vars, free_vertex, label)
        for label in range(order_vars.span + 1)
        if abs(fixed_label - label) < minimum_difference
    ]


def strict_less_clauses(
    order_vars: OrderVars, smaller: int, larger: int
) -> list[list[int]]:
    """Encode f(smaller) < f(larger) in order encoding."""
    fixed_clauses = _fixed_strict_less_clauses(order_vars, smaller, larger)
    if fixed_clauses is not None:
        return fixed_clauses
    if order_vars.span == 0:
        return [[]]
    clauses = [[order_vars.x[smaller][order_vars.span - 1]]]
    clauses.extend(
        [-order_vars.x[larger][threshold], order_vars.x[smaller][threshold - 1]]
        for threshold in range(1, order_vars.span)
    )
    clauses.append([-order_vars.x[larger][0]])
    return clauses


def _fixed_strict_less_clauses(
    order_vars: OrderVars, smaller: int, larger: int
) -> list[list[int]] | None:
    smaller_fixed = order_vars.fixed_labels.get(smaller)
    larger_fixed = order_vars.fixed_labels.get(larger)
    if smaller_fixed is None and larger_fixed is None:
        return None
    if smaller_fixed is not None and larger_fixed is not None:
        return [[]] if smaller_fixed >= larger_fixed else []
    if smaller_fixed is not None:
        return [[-order_vars.x[larger][smaller_fixed]]] if smaller_fixed < order_vars.span else [[]]
    threshold = larger_fixed - 1
    return [[order_vars.x[smaller][threshold]]] if threshold >= 0 else [[]]


def symmetry_breaking_clauses(
    order_vars: OrderVars,
    symmetry_kind: str | None,
    symmetry_vertices: tuple[int, int, int] | None = None,
) -> list[list[int]]:
    """Add sound symmetry constraints for supported graph families."""
    if not symmetry_kind or order_vars.n_vertices == 0:
        return []
    if symmetry_kind in {"CORONA", "STRUCTURAL"}:
        if symmetry_vertices is None:
            return []
        _, first_neighbor, second_neighbor = symmetry_vertices
        if max(symmetry_vertices) >= order_vars.n_vertices:
            return []
        return strict_less_clauses(
            order_vars, first_neighbor, second_neighbor
        )
    builders = {
        "P": _path_symmetry,
        "C": _cycle_symmetry,
        "K": _complete_symmetry,
        "Q": _hypercube_symmetry,
    }
    builder = builders.get(symmetry_kind)
    return builder(order_vars) if builder else []


def _path_symmetry(order_vars: OrderVars) -> list[list[int]]:
    # Endpoints can have equal labels in an optimum: strict order is unsound.
    return []


def _cycle_symmetry(order_vars: OrderVars) -> list[list[int]]:
    if order_vars.n_vertices < 3:
        return []
    return strict_less_clauses(order_vars, 1, order_vars.n_vertices - 1)


def _complete_symmetry(order_vars: OrderVars) -> list[list[int]]:
    if order_vars.n_vertices < 2:
        return []
    clauses = []
    for vertex in range(order_vars.n_vertices - 1):
        clauses += strict_less_clauses(order_vars, vertex, vertex + 1)
    return clauses


def _hypercube_symmetry(order_vars: OrderVars) -> list[list[int]]:
    dimension = order_vars.n_vertices.bit_length() - 1
    if dimension < 1 or 2**dimension != order_vars.n_vertices:
        return []
    clauses = []
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
    symmetry_vertices: tuple[int, int, int] | None = None,
    fixed_labels: dict[int, int] | None = None,
    simplify: bool = True,
) -> tuple[list[list[int]] | None, OrderVars]:
    """Build CNF; callers supplying symmetries must justify their soundness."""
    if h < 0 or k < 0:
        raise ValueError("separation thresholds must be non-negative")
    if symmetry_kind and min(h, k) < 1:
        raise ValueError("strict symmetry orders require positive separation gaps")
    fixed = dict(fixed_labels or {})
    if symmetry_kind == "C" and n_vertices > 0:
        fixed.setdefault(0, 0)
    order_vars = OrderVars(n_vertices, span, fixed)
    clauses = monotone_clauses(order_vars)
    clauses += symmetry_breaking_clauses(
        order_vars, symmetry_kind, symmetry_vertices
    )
    for first, second in edges:
        clauses += forbid_close_labels(order_vars, first, second, h)
    for first, second in distance_two_pairs:
        clauses += forbid_close_labels(order_vars, first, second, k)
    order_vars.raw_clause_count = len(clauses)
    if simplify:
        clauses = simplify_cnf(clauses)
    if any(not clause for clause in clauses):
        return None, order_vars
    return clauses, order_vars
