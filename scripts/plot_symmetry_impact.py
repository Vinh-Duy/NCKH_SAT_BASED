"""Plot runtime and clause differences caused by SAT symmetry breaking."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "results" / "symmetry_comparison_benchmark.csv"
OUTPUT_DIR = ROOT / "results" / "plots"

REQUIRED_COLUMNS = {
    "Graph",
    "V",
    "Clause_Base",
    "Clause_Sym",
    "Time_Base",
    "Time_Sym",
}
METRIC_COLUMNS = [
    "Clause_Base",
    "Clause_Sym",
    "Time_Base",
    "Time_Sym",
]
FAMILY_PREFIXES = {
    "cartesian": "Cartesian Products (Grid / Mesh)",
    "corona": "Corona Products",
    "petersen": "Petersen Graphs",
}


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
    frame["Runtime_Delta"] = frame["Time_Base"] - frame["Time_Sym"]
    frame["Clause_Delta"] = frame["Clause_Base"] - frame["Clause_Sym"]
    return frame


def _family_for_graph(graph_name: str) -> str:
    if graph_name.startswith("GP_"):
        return "petersen"
    if "x" in graph_name:
        return "cartesian"
    if "o" in graph_name:
        return "corona"
    raise ValueError(f"Cannot determine graph family for {graph_name!r}")


def _group_by_family(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    frame = frame.copy()
    frame["Family"] = frame["Graph"].map(_family_for_graph)
    return {
        family: (
            frame.loc[frame["Family"] == family]
            .groupby("V", as_index=False)[["Runtime_Delta", "Clause_Delta"]]
            .mean()
            .sort_values("V")
        )
        for family in FAMILY_PREFIXES
    }


def _plot_delta(
    frame: pd.DataFrame,
    delta_column: str,
    title: str,
    y_label: str,
    filename: str,
) -> None:
    figure, axis = plt.subplots(figsize=(11, 6.5))
    axis.plot(
        frame["V"],
        frame[delta_column],
        color="tab:blue",
        linestyle="-",
        linewidth=2,
        marker="o",
        markersize=4,
    )
    axis.axhline(0, color="black", linewidth=0.9, alpha=0.7)
    axis.set_title(title, fontsize=14, pad=12)
    axis.set_xlabel("Number of vertices V")
    axis.set_ylabel(y_label)
    axis.grid(True, linestyle=":", alpha=0.65)
    figure.tight_layout()
    figure.savefig(OUTPUT_DIR / filename, dpi=300, bbox_inches="tight")
    plt.close(figure)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    frame = _load_data()
    families = _group_by_family(frame)
    plot_specs = (
        ("Runtime_Delta", "Runtime delta (seconds)", "delta_runtime"),
        ("Clause_Delta", "Clause delta", "delta_clauses"),
    )
    saved = 0
    for family, family_frame in families.items():
        if family_frame.empty:
            print(f"Skipped {FAMILY_PREFIXES[family]}: no rows in {INPUT.name}")
            continue
        for delta_column, y_label, filename_prefix in plot_specs:
            _plot_delta(
                family_frame,
                delta_column,
                f"{FAMILY_PREFIXES[family]}: {y_label}",
                y_label,
                f"{filename_prefix}_{family}.png",
            )
            saved += 1
    print(f"Saved {saved} plots to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
