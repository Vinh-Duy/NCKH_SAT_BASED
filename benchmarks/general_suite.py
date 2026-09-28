"""Predeclared graph cohort; no filtering by connectivity or solver outcome."""

import networkx as nx

from src.core.graph_utils import get_cartesian_path_path

SUITE_NAME = "general-pilot-v1"


def general_pilot():
    """39 graphs: 9 trees, 3 grids, 18 G(n,p), 9 preferential-attachment graphs.

    Seeds identify generated inputs, not solver random seeds. Disconnected
    G(n,p) samples are retained, including every isolated vertex.
    """
    for n in (20, 40, 60):
        for seed in (0, 1, 2):
            yield f"tree_{n}_seed{seed}", "tree", nx.random_labeled_tree(n, seed=seed)
    for n, m in ((4, 5), (5, 8), (6, 10)):
        yield f"P_{n}xP_{m}", "PxP", get_cartesian_path_path(n, m)
    for n in (20, 40, 60):
        for p in (0.15, 0.30):
            for seed in (0, 1, 2):
                yield f"ER_{n}_p{p:.2f}_seed{seed}", "ER", nx.gnp_random_graph(n, p, seed=seed)
        for seed in (0, 1, 2):
            yield f"BA_{n}_m2_seed{seed}", "BA", nx.barabasi_albert_graph(n, 2, seed=seed)
