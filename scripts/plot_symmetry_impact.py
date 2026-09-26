"""Plot symmetry effects separately for each graph family."""

from __future__ import annotations

from pathlib import Path
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "results" / "symmetry_comparison_benchmark.csv"
OUTPUT_DIR = ROOT / "paper" / "generated" / "plots"
FAMILIES = {
    "C": "Cycles C_n",
    "CxC": "Cycle × Cycle", "CxP": "Cycle × Path", "PxP": "Path × Path",
    "CoC": "Cycle ∘ Cycle", "CoP": "Cycle ∘ Path", "PoC": "Path ∘ Cycle",
    "PoP": "Path ∘ Path", "petersen": "Petersen",
}


def _family_for_graph(name):
    if re.fullmatch(r"C_\d+", name):
        return "C"
    if name.startswith("GP_"):
        return "petersen"
    match = re.fullmatch(r"([CP])_\d+([xo])([CP])_\d+", name)
    if match is None:
        raise ValueError(f"Cannot determine graph family for {name!r}")
    return "".join(match.groups())


def _load_data(path):
    frame = pd.read_csv(path)
    if not {"Graph", "V", "Clause_Base", "Clause_Sym"}.issubset(frame.columns):
        raise ValueError("CSV needs Graph,V,Clause_Base,Clause_Sym")
    frame["Family"] = frame["Graph"].map(_family_for_graph)
    frame["V"] = pd.to_numeric(frame["V"], errors="raise")
    paired = {"Status_Base", "Status_Sym"}.issubset(frame.columns)
    if paired:
        frame = frame[(frame["Status_Base"] == "OPT") & (frame["Status_Sym"] == "OPT")].copy()
        if {"lambda_Base", "lambda_Sym"}.issubset(frame.columns):
            if not frame["lambda_Base"].eq(frame["lambda_Sym"]).all():
                raise ValueError("optimal spans disagree; do not aggregate runtimes")
        else:
            print("Legacy CSV: paired spans cannot be checked; timings are historical observations.")
    if "Count_Span" not in frame:
        print("Legacy clause counts: a common encoding span was not recorded.")
    specs = [("Clause", "Clause delta", "delta_clauses")]
    if paired and {"Time_Base", "Time_Sym"}.issubset(frame.columns):
        specs.insert(0, ("Time", "Runtime delta (seconds)", "delta_runtime"))
    for metric, _, _ in specs:
        base = pd.to_numeric(frame[f"{metric}_Base"], errors="coerce")
        sym = pd.to_numeric(frame[f"{metric}_Sym"], errors="coerce")
        frame[f"{metric}_Delta"] = base - sym
    return frame, specs


def _plot(frame, metric, ylabel, title, output):
    figure, axis = plt.subplots(figsize=(10, 6))
    for family, group in frame.groupby("Family", sort=True):
        group = group.dropna(subset=[f"{metric}_Delta"])
        if group.empty:
            continue
        grouped = group.groupby("V")[f"{metric}_Delta"].mean().sort_index()
        axis.plot(grouped.index, grouped.values, marker="o", markersize=4,
                  label=FAMILIES[family])
    axis.axhline(0, color="black", linewidth=0.9, alpha=0.7)
    axis.set(title=title, xlabel="Number of vertices V", ylabel=ylabel + " (Base − Sym)")
    axis.grid(True, linestyle=":", alpha=0.65)
    axis.legend()
    figure.tight_layout()
    figure.savefig(output, dpi=200, bbox_inches="tight")
    plt.close(figure)


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=INPUT)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    frame, specs = _load_data(args.input)
    saved = 0
    for metric, ylabel, prefix in specs:
        valid = frame.dropna(subset=[f"{metric}_Delta"])
        for family, group in valid.groupby("Family", sort=True):
            title = FAMILIES[family]
            if "Symmetry_Rule" in group and group["Symmetry_Rule"].eq("none").all():
                title += " (same model, repeated runs)"
            _plot(group, metric, ylabel, title,
                  args.output_dir / f"{prefix}_{family}.png")
            saved += 1
        # Existing manuscript paths remain available, with distinct family curves
        # instead of pooling structurally different families into a single mean.
        for category, families in (("cartesian", {"CxC", "CxP", "PxP"}),
                                   ("corona", {"CoC", "CoP", "PoC", "PoP"})):
            group = valid[valid["Family"].isin(families)]
            if not group.empty:
                _plot(group, metric, ylabel, category.title(),
                      args.output_dir / f"{prefix}_{category}.png")
                saved += 1
    print(f"Saved {saved} plots to {args.output_dir}")


if __name__ == "__main__":
    main()
