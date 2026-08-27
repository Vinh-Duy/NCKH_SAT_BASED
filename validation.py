from collections.abc import Mapping


def format_bound_history(bounds):
    """Format tested upper bounds for storage in a CSV result row."""
    return " -> ".join(str(bound) for bound in bounds)


def labels_from_model(n_vertices, span, model, order_vars):
    model_literals = set(model)
    labels = {}
    for vertex in range(n_vertices):
        labels[vertex] = next(
            (index for index in range(span) if order_vars.x[vertex][index] in model_literals),
            span,
        )
    return labels


def validate_labeling(n_vertices, edges, dist2_pairs, span, labels, h=2, k=1):
    errors = []

    if not isinstance(span, int) or isinstance(span, bool) or span < 0:
        errors.append(f"span must be a non-negative integer, got {span!r}")
        return False, errors

    if not isinstance(labels, Mapping):
        return False, ["labels must be a mapping from vertex to label"]

    expected_vertices = set(range(n_vertices))
    actual_vertices = set(labels)
    missing = expected_vertices - actual_vertices
    extra = actual_vertices - expected_vertices
    if missing:
        errors.append(f"missing labels for vertices: {sorted(missing)}")
    if extra:
        errors.append(f"labels contain unknown vertices: {sorted(extra)}")

    for vertex in sorted(expected_vertices & actual_vertices):
        label = labels[vertex]
        if not isinstance(label, int) or isinstance(label, bool):
            errors.append(f"vertex {vertex} has non-integer label {label!r}")
        elif label < 0 or label > span:
            errors.append(
                f"vertex {vertex} has label {label}, outside 0..{span}"
            )

    def check_pairs(pairs, minimum_difference, relation):
        for first, second in pairs:
            if first not in labels or second not in labels:
                continue
            difference = abs(labels[first] - labels[second])
            if difference < minimum_difference:
                errors.append(
                    f"{relation} pair ({first}, {second}) has label "
                    f"difference {difference}, requires >= {minimum_difference}"
                )

    check_pairs(edges, h, "edge")
    check_pairs(dist2_pairs, k, "distance-2")
    return not errors, errors