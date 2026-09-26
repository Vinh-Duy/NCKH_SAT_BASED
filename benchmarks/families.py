"""One shared definition of the seven product benchmark families."""

from src.core.graph_utils import (
    get_cartesian_cycle_cycle, get_cartesian_cycle_path,
    get_cartesian_path_path, get_corona_graph,
)


def product_instances(n, m):
    yield f"C_{n}xC_{m}", get_cartesian_cycle_cycle(n, m)
    yield f"C_{n}xP_{m}", get_cartesian_cycle_path(n, m)
    yield f"P_{n}xP_{m}", get_cartesian_path_path(n, m)
    for left, right in (("C", "C"), ("P", "P"), ("C", "P"), ("P", "C")):
        yield f"{left}_{n}o{right}_{m}", get_corona_graph(left, right, n, m)
