from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


INPUT_PATH = Path("results/ket_qua_hybrid.csv")
OUTPUT_PATH = Path("results/bieu_do_lambda.png")
GRAPH_TYPES = {
    "C": "Cycle",
    "K": "Complete",
    "Q": "Hypercube",
}


def load_results(path):
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    data = pd.read_csv(path)
    required_columns = {"Graph", "n", "lambda", "status"}
    missing_columns = required_columns - set(data.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Missing required CSV columns: {missing}")

    data["lambda"] = pd.to_numeric(data["lambda"], errors="coerce")
    data["n"] = pd.to_numeric(data["n"], errors="coerce")
    data = data.dropna(subset=["lambda", "n"])
    data = data[data["status"].astype(str).str.upper() != "INVALID"]
    data["type"] = data["Graph"].astype(str).str[:1].str.upper()
    return data[data["type"].isin(GRAPH_TYPES)]


def plot_results(data, output_path):
    figure, axes = plt.subplots(1, 3, figsize=(18, 5), constrained_layout=True)

    colors = {"C": "#2563eb", "K": "#dc2626", "Q": "#059669"}
    for axis, (graph_type, title) in zip(axes, GRAPH_TYPES.items()):
        group = data[data["type"] == graph_type].sort_values("n")
        axis.plot(
            group["n"],
            group["lambda"],
            marker="o",
            markersize=4,
            linewidth=1.8,
            color=colors[graph_type],
        )
        axis.set_title(f"{title} graphs ({graph_type})")
        axis.set_xlabel("Number of vertices (n)")
        axis.set_ylabel("Lambda")
        axis.grid(True, linestyle="--", alpha=0.45)

    figure.suptitle("Growth of Lambda by Graph Family", fontsize=15, fontweight="bold")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=180, bbox_inches="tight")
    plt.close(figure)


def main():
    data = load_results(INPUT_PATH)
    plot_results(data, OUTPUT_PATH)
    print(f"Saved plot to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
