"""Plot the impact of SAT symmetry breaking on product benchmarks."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "results" / "symmetry_comparison_benchmark.csv"
OUTPUT_DIR = ROOT / "results" / "plots"

REQUIRED_COLUMNS = {
    "V",
    "Var_Base",
    "Var_Sym",
    "Clause_Base",
    "Clause_Sym",
    "Time_Base",
    "Time_Sym",
}
METRIC_COLUMNS = [
    "Var_Base",
    "Var_Sym",
    "Clause_Base",
    "Clause_Sym",
    "Time_Base",
    "Time_Sym",
]


def _load_data() -> pd.DataFrame:
    frame = pd.read_csv(INPUT)
    missing = REQUIRED_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
    numeric_columns = ["V", *METRIC_COLUMNS]
    frame[numeric_columns] = frame[numeric_columns].apply(
        pd.to_numeric, errors="coerce"
    )
    frame = frame.dropna(subset=numeric_columns)
    return frame.groupby("V", as_index=False)[METRIC_COLUMNS].mean().sort_values("V")


def _plot_comparison(
    frame: pd.DataFrame,
    base_column: str,
    symmetry_column: str,
    title: str,
    y_label: str,
    filename: str,
) -> None:
    figure, axis = plt.subplots(figsize=(11, 6.5))
    axis.plot(
        frame["V"],
        frame[base_column],
        color="red",
        linestyle="--",
        linewidth=2,
        marker="o",
        markersize=4,
        label="Baseline (No Sym)",
    )
    axis.plot(
        frame["V"],
        frame[symmetry_column],
        color="royalblue",
        linestyle="-",
        linewidth=2,
        marker="o",
        markersize=4,
        label="With Symmetry Breaking",
    )
    axis.set_title(title, fontsize=14, pad=12)
    axis.set_xlabel("Number of vertices V")
    axis.set_ylabel(y_label)
    axis.grid(True, linestyle=":", alpha=0.65)
    axis.legend()
    figure.tight_layout()
    figure.savefig(OUTPUT_DIR / filename, dpi=300, bbox_inches="tight")
    plt.close(figure)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    frame = _load_data()
    _plot_comparison(
        frame,
        "Var_Base",
        "Var_Sym",
        "SAT Variables: Baseline vs Symmetry Breaking",
        "Number of SAT variables",
        "var_reduction_comparison.png",
    )
    _plot_comparison(
        frame,
        "Clause_Base",
        "Clause_Sym",
        "SAT Clauses: Baseline vs Symmetry Breaking",
        "Number of SAT clauses",
        "clause_reduction_comparison.png",
    )
    _plot_comparison(
        frame,
        "Time_Base",
        "Time_Sym",
        "Runtime: Baseline vs Symmetry Breaking",
        "Runtime (seconds)",
        "runtime_improvement_comparison.png",
    )
    print(f"Saved 3 plots to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
