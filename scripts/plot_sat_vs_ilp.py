"""Plot paired comparison CSVs without treating missing solvers as timeouts."""

import argparse
import csv
import json
import math
from pathlib import Path
import statistics

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

FAMILY_LABELS = {
    "PxP": r"$P_n\,□\,P_m$", "CxC": r"$C_n\,□\,C_m$",
    "CxP": r"$C_n\,□\,P_m$", "CoP": r"$C_n\circ P_m$",
    "Q": r"$Q_d$", "tree": "Random trees",
    "ER": r"Erdős–Rényi $G(n,p)$", "BA": "Barabási–Albert (m=2)",
}

VALID_STATUSES = {"OPT", "FEASIBLE", "TIMEOUT", "UNAVAILABLE", "SKIPPED", "ERROR", "INVALID", "INFEASIBLE"}
KEY = ("Instance", "h", "k", "Repeat")


def load_rows(path):
    with Path(path).open(newline="") as source:
        rows = list(csv.DictReader(source))
    seen = set()
    for row in rows:
        identity = tuple(row[key] for key in (*KEY, "Method"))
        if identity in seen:
            raise ValueError(f"duplicate observation: {identity}")
        seen.add(identity)
        if row["Status"] not in VALID_STATUSES:
            raise ValueError(f"unknown status: {row['Status']}")
        for field in ("h", "k", "Repeat", "V"):
            row[field] = int(row[field])
        row["Limit"] = float(row["Limit"])
        row["Wall_Time"] = float(row["Wall_Time"]) if row["Wall_Time"] else None
        if not math.isfinite(row["Limit"]) or row["Limit"] <= 0:
            raise ValueError("invalid time limit")
        if row["Wall_Time"] is not None and (not math.isfinite(row["Wall_Time"]) or row["Wall_Time"] < 0):
            raise ValueError("invalid runtime")
        if row["Status"] == "OPT" and (row["Wall_Time"] is None or row["Wall_Time"] <= 0):
            raise ValueError("OPT requires a positive observed runtime")
    return rows


def paired_cohort(rows):
    """All methods must actually run; solved and unresolved instances both remain."""
    methods = {row["Method"] for row in rows}
    groups = {}
    for row in rows:
        groups.setdefault(tuple(row[key] for key in KEY), []).append(row)
    paired = []
    for group in groups.values():
        if {row["Method"] for row in group} != methods:
            continue
        if len({row["Limit"] for row in group}) != 1 or len({row["V"] for row in group}) != 1:
            raise ValueError("paired rows disagree on budget or graph size")
        if any(row["Status"] not in {"OPT", "FEASIBLE", "TIMEOUT"} for row in group):
            continue
        optima = {row["Span"] for row in group if row["Status"] == "OPT"}
        if len(optima) > 1:
            raise ValueError("solvers disagree on the optimum")
        paired.extend(group)
    return sorted(methods), paired


def plot(input_path, output):
    rows = load_rows(input_path)
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise FileExistsError("use a fresh output directory to avoid mixing stale plots")
    output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "serif", "font.size": 10, "mathtext.fontset": "dejavuserif", "text.usetex": False})
    coverage = []
    for family, h, k in sorted({(r["Family"], r["h"], r["k"]) for r in rows}):
        selected = [r for r in rows if (r["Family"], r["h"], r["k"]) == (family, h, k)]
        methods, cohort = paired_cohort(selected)
        count = len(cohort)//len(methods)
        coverage.append(dict(family=family, h=h, k=k, paired_observations=count,
                             status_counts={method: {status: sum(r["Method"] == method and r["Status"] == status for r in selected)
                                                     for status in sorted(VALID_STATUSES)} for method in methods}))
        if not cohort or len(methods) < 2:
            continue  # No fabricated comparison when a proprietary solver is missing.
        prefix = f"{family}_h{h}_k{k}"
        label = FAMILY_LABELS.get(family, family)
        graph_count = len({r["Instance"] for r in cohort})
        fig, ax = plt.subplots(figsize=(5.5, 3.6))
        for method in methods:
            times = sorted(r["Wall_Time"] for r in cohort if r["Method"] == method
                           and r["Status"] == "OPT" and r["Wall_Time"] <= r["Limit"])
            ax.step([0]+times, list(range(len(times)+1)), where="post", label=method)
        ax.set(xlabel="Wall time (s)", ylabel="Observations proved optimal",
               title=label + rf", $L({h},{k})$" + f"; {graph_count} graphs, {count} pairs")
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.legend(); ax.grid(alpha=.2); fig.tight_layout()
        for ext in ("png", "pdf"):
            fig.savefig(output/f"{prefix}_cactus.{ext}", dpi=300)
        plt.close(fig)
        groups = {}
        for row in cohort:
            groups.setdefault(tuple(row[key] for key in KEY), []).append(row)
        jointly_opt = [r for group in groups.values()
                       if all(x["Status"] == "OPT" and x["Wall_Time"] <= x["Limit"] for x in group)
                       for r in group]
        if not jointly_opt:
            continue
        fig, ax = plt.subplots(figsize=(5.5, 3.6))
        for method in methods:
            by_size = {}
            for row in jointly_opt:
                if row["Method"] == method:
                    by_size.setdefault(row["V"], []).append(row["Wall_Time"])
            sizes = sorted(by_size)
            ax.plot(sizes, [statistics.median(by_size[n]) for n in sizes], marker="o", label=method)
        ax.set(xlabel=r"Number of vertices $|V|$", ylabel="Median wall time (s)", yscale="log",
               title=label + rf", $L({h},{k})$; jointly OPT only")
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.legend(); ax.grid(alpha=.2); fig.tight_layout()
        for ext in ("png", "pdf"):
            fig.savefig(output/f"{prefix}_runtime.{ext}", dpi=300)
        plt.close(fig)
    (output/"coverage.json").write_text(json.dumps(coverage, indent=2)+"\n")
    (output/"README.txt").write_text(
        "Cactus counts instance/repetition observations, not distinct graphs.\n"
        "Only equal-budget observations with every method available are paired.\n"
        "Only OPT within the budget counts as solved; FEASIBLE/TIMEOUT do not.\n"
        "Runtime lines show medians by size on jointly OPT observations (selection bias).\n"
        "Interpret alongside cactus/coverage; no conclusion of universal superiority.\n"
        "Missing solver -> no comparison plot. See coverage.json.\n")
    return coverage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(plot(args.input, args.output_dir), indent=2))


if __name__ == "__main__":
    main()
