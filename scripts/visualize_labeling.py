"""Visualize an L(2,1)-labeling returned by the SAT solver."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Hashable, Mapping

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.colors import Normalize

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.core.graph_utils import cycle_graph
from src.solvers.sat_solver import solve_graph


OUTPUT_DIR = ROOT / "paper" / "generated" / "plots"


def plot_labeling(
    graph: nx.Graph,
    labels: Mapping[Hashable, int],
    graph_name: str,
    span: int | None = None,
    output_dir: str | Path = OUTPUT_DIR,
) -> Path:
    """Draw and save a graph with its L(2,1) labels shown on every node."""
    missing = set(graph.nodes()).difference(labels)
    if missing:
        raise ValueError(f"Missing labels for graph nodes: {sorted(missing, key=str)}")

    label_values = {node: int(labels[node]) for node in graph.nodes()}
    if span is None:
        span = max(label_values.values(), default=0) - min(
            label_values.values(), default=0
        )

    output_path = Path(output_dir) / f"{graph_name}_labeling.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(12, 8))
    positions = nx.spring_layout(graph, seed=42)
    values = list(label_values.values())
    normalizer = Normalize(vmin=min(values, default=0), vmax=max(values, default=1))
    node_colors = [label_values[node] for node in graph.nodes()]
    node_labels = {
        node: f"Đỉnh {node}\nL={label_values[node]}" for node in graph.nodes()
    }

    nx.draw_networkx_edges(
        graph,
        positions,
        ax=axis,
        edge_color="#555555",
        width=1.5,
        alpha=0.8,
    )
    nodes = nx.draw_networkx_nodes(
        graph,
        positions,
        ax=axis,
        node_color=node_colors,
        cmap="viridis",
        node_size=1500,
        edgecolors="black",
        linewidths=1.0,
        vmin=normalizer.vmin,
        vmax=normalizer.vmax,
    )
    nx.draw_networkx_labels(
        graph,
        positions,
        labels=node_labels,
        ax=axis,
        font_size=8,
        font_weight="bold",
    )
    figure.colorbar(nodes, ax=axis, label="Label value f(v)")
    axis.set_title(f"L(2,1)-labeling of {graph_name} (lambda = {span})")
    axis.axis("off")
    figure.tight_layout()
    figure.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(figure)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Solve C_n and visualize its L(2,1)-labeling"
    )
    parser.add_argument("--n", type=int, default=6, help="Cycle size")
    parser.add_argument("--name", default=None, help="Output graph name")
    args = parser.parse_args()

    graph_name = args.name or f"C_{args.n}"
    graph = cycle_graph(args.n)
    result = solve_graph(graph, solver_name="glucose", strategy="hybrid")
    output_path = plot_labeling(
        graph,
        result.labels,
        graph_name,
        span=result.span,
    )
    print(f"Saved labeling plot to {output_path}")


if __name__ == "__main__":
    main()
