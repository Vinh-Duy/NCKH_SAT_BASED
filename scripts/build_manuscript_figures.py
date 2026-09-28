"""Create original vector illustrations and plots from the audited tree screen."""

import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import networkx as nx
import numpy as np

from scripts.export_tree_screen import audit
from src.core.validator import validate_labeling


def example_labeling():
    graph = nx.path_graph(5)
    labels = dict(enumerate([0, 3, 6, 1, 4]))
    distance_two = [(0, 2), (1, 3), (2, 4)]
    valid, errors = validate_labeling(list(graph.edges()), distance_two, labels, 6, 3, 2, vertices=graph)
    if not valid:
        raise ValueError(errors)
    return graph, labels


def save(fig, directory, name):
    fig.savefig(directory/f"{name}.pdf", bbox_inches="tight",
                metadata={"CreationDate": None, "ModDate": None})
    fig.savefig(directory/f"{name}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def illustration(directory):
    graph, labels = example_labeling()
    fig, (left, right) = plt.subplots(1, 2, figsize=(7.2, 2.6), layout="constrained")
    positions = {v: (v, 0) for v in graph}
    nx.draw_networkx_edges(graph, positions, ax=left, width=1.6, edge_color="#333333")
    nx.draw_networkx_nodes(graph, positions, ax=left, node_size=600,
                          node_color="#e4edf4", edgecolors="#254e70")
    nx.draw_networkx_labels(graph, positions, labels=labels, ax=left, font_size=12)
    for v in graph:
        left.text(v, -0.3, f"$v_{v}$", ha="center", fontsize=10)
    arc = FancyArrowPatch((0, 0.15), (2, 0.15), connectionstyle="arc3,rad=-0.5",
                          arrowstyle="-", linestyle="--", color="#a34d22", linewidth=1.5)
    left.add_patch(arc)
    left.text(1, 0.69, r"$d(v_0,v_2)=2$", ha="center", fontsize=10)
    left.text(2, -0.75, r"$L(3,2),\quad s=6$", ha="center", fontsize=11)
    left.text(0, 1, "(a)", transform=left.transAxes, va="top")
    left.set(xlim=(-0.55, 4.55), ylim=(-1, 1.15))
    left.axis("off")
    order = np.array([[int(labels[v] <= i) for i in range(6)] for v in graph])
    right.imshow(order, cmap=ListedColormap(["#ffffff", "#d8e8f2"]), vmin=0, vmax=1, aspect="auto")
    for v in graph:
        for i in range(6):
            right.text(i, v, str(order[v, i]), ha="center", va="center", fontsize=10)
    right.set(xticks=range(6), yticks=range(5),
              yticklabels=[f"$v_{v}$ ({labels[v]})" for v in graph], xlabel="Threshold $i$")
    right.set_xticks(np.arange(-0.5, 6), minor=True)
    right.set_yticks(np.arange(-0.5, 5), minor=True)
    right.grid(which="minor", color="#aaaaaa", linewidth=0.5)
    right.tick_params(which="minor", bottom=False, left=False)
    right.text(-0.18, 1.04, "(b)", transform=right.transAxes)
    save(fig, directory, "labeling_order")


def pipeline(directory):
    fig, ax = plt.subplots(figsize=(7.2, 2.15), layout="constrained")
    centers = [0.65, 2.15, 3.65, 5.15, 6.65]
    texts = ["Graph $G$\nParameters $h,k$", "$E, D_2(G)$\nBounds $L,U$",
             "Choose span $s$\nBuild CNF$(s)$", "SAT solver\nSAT / UNSAT",
             "Validate witness\nUpdate bounds"]
    for x, label in zip(centers, texts):
        ax.add_patch(FancyBboxPatch((x-0.61, 0.82), 1.22, 0.55,
                                   boxstyle="round,pad=0.03", linewidth=0.9,
                                   facecolor="#eef3f7", edgecolor="#35566d"))
        ax.text(x, 1.095, label, ha="center", va="center", fontsize=8.5)
    for x, y in zip(centers, centers[1:]):
        ax.annotate("", (y-0.64, 1.1), (x+0.64, 1.1), arrowprops=dict(arrowstyle="->", lw=1))
    ax.plot([6.65, 6.65, 3.65], [0.79, 0.48, 0.48], color="#333333", lw=1)
    ax.annotate("", (3.65, 0.79), (3.65, 0.48), arrowprops=dict(arrowstyle="->", lw=1))
    ax.text(5.15, 0.20, "$L<U$: next span, fresh solver", ha="center", fontsize=9)
    ax.text(3.65, -0.12, "$L=U$: OPT     |     budget exhausted: FEASIBLE + witness", ha="center", fontsize=9)
    ax.set(xlim=(-0.05, 7.4), ylim=(-0.26, 1.6))
    ax.axis("off")
    save(fig, directory, "solver_pipeline")


def results_figure(rows, directory):
    fig, (left, right) = plt.subplots(1, 2, figsize=(7.2, 3.0), layout="constrained")
    sizes = sorted({int(r["V"]) for r in rows})
    for method, color, marker in [("cadical", "#24557b", "o"), ("gurobi", "#ac4f1f", "s")]:
        samples = [[float(r["Wall_Time"]) for r in rows if r["Method"] == method and int(r["V"]) == n] for n in sizes]
        quantiles = np.array([np.percentile(sample, [25, 50, 75]) for sample in samples])
        label = {"cadical": "CaDiCaL", "gurobi": "Gurobi"}[method]
        left.plot(sizes, quantiles[:, 1], marker=marker, color=color, label=label)
        left.fill_between(sizes, quantiles[:, 0], quantiles[:, 2], color=color, alpha=0.13)
    left.set(xscale="log", yscale="log", xlabel="Vertices $|V|$", ylabel="Wall time (s)")
    left.set_xticks(sizes, labels=[str(n) for n in sizes])
    left.tick_params(axis="x", labelsize=8)
    left.legend(frameon=False, fontsize=9)
    pairs = {}
    for row in rows:
        pairs.setdefault((row["Instance"], row["Repeat"]), {})[row["Method"]] = float(row["Wall_Time"])
    xs = [pair["gurobi"] for pair in pairs.values()]
    ys = [pair["cadical"] for pair in pairs.values()]
    low, high = min(xs+ys)*0.8, max(xs+ys)*1.2
    right.plot([low, high], [low, high], "--", color="#666666", lw=1, label="Equal wall time")
    right.scatter(xs, ys, s=22, color="#24557b", alpha=0.7)
    right.set(xscale="log", yscale="log", xlim=(low, high), ylim=(low, high),
              xlabel="Gurobi wall time (s)", ylabel="CaDiCaL wall time (s)")
    right.legend(frameon=False, fontsize=8, loc="upper left")
    for tag, ax in zip(("(a)", "(b)"), (left, right)):
        ax.text(0, 1.03, tag, transform=ax.transAxes)
        ax.grid(alpha=0.2, which="major")
    save(fig, directory, "tree_runtime")


def build(input_path, output_dir):
    checked = audit(input_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Serif", "font.size": 10,
                         "mathtext.fontset": "dejavuserif", "pdf.fonttype": 42,
                         "ps.fonttype": 42, "text.usetex": False})
    with input_path.open(newline="") as source:
        rows = list(csv.DictReader(source))
    illustration(output_dir)
    pipeline(output_dir)
    results_figure(rows, output_dir)
    manifest = dict(inputs=checked["inputs"], observations=checked["observations"],
                    matplotlib=matplotlib.__version__, numpy=np.__version__,
                    script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                    auditor_sha256=hashlib.sha256((ROOT/"scripts/export_tree_screen.py").read_bytes()).hexdigest(),
                    scope="original validated example; implementation diagram; measured tree screen (median/IQR, paired scatter)")
    (output_dir/"sources.json").write_text(json.dumps(manifest, indent=2)+"\n")
    print(f"Generated 3 vector figures and PNG previews in {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT/"results/runs/tree_l32_screen_v2.csv")
    parser.add_argument("--output-dir", type=Path, default=ROOT/"paper/generated/manuscript_figures")
    args = parser.parse_args()
    build(args.input.resolve(), args.output_dir)
