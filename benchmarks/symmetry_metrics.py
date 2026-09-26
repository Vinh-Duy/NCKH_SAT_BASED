"""Measure two CNFs at one explicit span, independently of search history."""

import re
import networkx as nx

from src.core.graph_utils import graph_constraints
from src.models.sat_encoding import build_cnf
from src.solvers.sat_solver import _symmetry_plan


SIZE_FIELDS = [
    "Count_Span", "Symmetry_Rule", "Var_Base", "Var_Sym",
    "Clause_Raw_Base", "Clause_Raw_Sym", "Clause_Base", "Clause_Sym",
    "Var_Reduce_Pct", "Clause_Reduce_Pct",
]


def product_family(name):
    match = re.fullmatch(r"([CP])_\d+([xo])([CP])_\d+", name)
    if match is None:
        raise ValueError(f"unknown product name: {name}")
    return "".join(match.groups())


def compare_cnf_sizes(graph, span):
    """Count allocated variables and emitted clauses (including retained units).

    Raw means after fixed-root substitution but before shared preprocessing.
    Counts describe the supplied span, whether or not it is the optimum.
    No SAT solver is called, and no timing or optimality claim is made here.
    """
    graph = nx.relabel_nodes(graph, {v: i for i, v in enumerate(graph)}, copy=True)
    edges, d2 = graph_constraints(graph)
    row = {"Count_Span": span}
    for enabled, suffix in ((False, "Base"), (True, "Sym")):
        kind, vertices, fixed = _symmetry_plan(graph, None, enabled)
        cnf, variables = build_cnf(len(graph), edges, d2, span,
                                   symmetry_kind=kind, symmetry_vertices=vertices,
                                   fixed_labels=fixed)
        row[f"Var_{suffix}"] = variables.variable_count
        row[f"Clause_Raw_{suffix}"] = variables.raw_clause_count
        row[f"Clause_{suffix}"] = len(cnf) if cnf is not None else 1
        if enabled:
            rules = (["root=0"] if fixed else [])
            if vertices is not None or kind in {"C", "K", "Q"}:
                rules.append("order")
            row["Symmetry_Rule"] = "+".join(rules) or "none"
    for metric in ("Var", "Clause"):
        base, sym = row[f"{metric}_Base"], row[f"{metric}_Sym"]
        row[f"{metric}_Reduce_Pct"] = round(100 * (1 - sym / base), 4) if base else None
    return row
