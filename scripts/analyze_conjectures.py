from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "results" / "products_benchmark.csv"
OUTPUT = ROOT / "paper" / "generated" / "observations.txt"
GRAPH_PATTERN = re.compile(r"^(?P<left>[A-Za-z]+)_(?P<n>\d+)(?P<op>[xo])(?P<right>[A-Za-z]+)_(?P<m>\d+)$")


def _parse_graph_name(name: str) -> dict[str, object]:
    match = GRAPH_PATTERN.match(str(name))
    if match is None:
        raise ValueError(f"Unsupported graph name: {name}")
    data = match.groupdict()
    return {
        "family": f"{data['left']} {data['op']} {data['right']}",
        "n": int(data["n"]),
        "m": int(data["m"]),
    }


def _load_results() -> pd.DataFrame:
    frame = pd.read_csv(INPUT)
    required = {"Graph", "lambda", "status"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")
    parsed = frame["Graph"].map(_parse_graph_name).apply(pd.Series)
    frame = pd.concat([frame, parsed], axis=1)
    frame["lambda"] = pd.to_numeric(frame["lambda"], errors="coerce")
    frame["status"] = frame["status"].fillna("UNKNOWN").astype(str).str.upper()
    return frame


def _cell(row: pd.Series) -> str:
    value = "-" if pd.isna(row["lambda"]) else str(int(row["lambda"]))
    return f"{value} [{row['status']}]"


def _pivot_text(frame: pd.DataFrame) -> str:
    cells = frame.apply(_cell, axis=1)
    table = pd.DataFrame({"n": frame["n"], "m": frame["m"], "value": cells})
    pivot = table.pivot(index="n", columns="m", values="value").sort_index()
    pivot.index.name = "n"
    pivot.columns.name = "m"
    return pivot.fillna("-").to_string()


def _linear_summary(optimal: pd.DataFrame) -> str:
    if optimal.empty:
        return "No OPT rows are available for a formula check."

    candidates = _linear_candidates(optimal)

    periodic = _periodic_candidates(optimal)
    findings = []
    if candidates:
        findings.append("Exact linear patterns observed: " + "; ".join(candidates) + ".")
    if periodic:
        findings.append("Candidate periodic patterns: " + "; ".join(periodic) + ".")
    if findings:
        return " ".join(findings)

    values = optimal["lambda"].astype(int)
    counts = values.value_counts().sort_index()
    if len(counts) <= 3:
        distribution = ", ".join(f"{value} ({count} cases)" for value, count in counts.items())
        return f"No exact linear rule detected; lambda takes a small set of values: {distribution}."
    return "No exact linear rule detected in the OPT rows."


def _linear_candidates(optimal: pd.DataFrame) -> list[str]:
    candidates: list[str] = []
    for variable, label in (("n", "n"), ("m", "m")):
        residual = optimal["lambda"] - optimal[variable]
        if residual.nunique() == 1:
            candidates.append(f"lambda = {label} + {int(residual.iloc[0])}")
    residual = optimal["lambda"] - optimal["n"] - optimal["m"]
    if residual.nunique() == 1:
        candidates.append(f"lambda = n+m + {int(residual.iloc[0])}")
    return candidates


def _periodic_candidates(optimal: pd.DataFrame) -> list[str]:
    candidates: list[str] = []
    for variable, label in (("n", "n"), ("m", "m")):
        for period in (2, 3):
            grouped = optimal.groupby(optimal[variable] % period)["lambda"]
            if optimal["lambda"].nunique() > 1 and len(grouped) >= 2 and all(len(values) >= 2 and values.nunique() == 1 for _, values in grouped):
                pattern = ", ".join(
                    f"{remainder}->{int(values.iloc[0])}"
                    for remainder, values in grouped
                )
                candidates.append(f"{label} mod {period} ({pattern})")
    return candidates


def _conjecture(family: str, frame: pd.DataFrame, optimal: pd.DataFrame) -> str:
    if optimal.empty:
        return f"Conjecture unavailable for {family}: no OPT instances."
    minimum = int(optimal["lambda"].min())
    maximum = int(optimal["lambda"].max())
    if minimum == maximum:
        statement = f"For tested parameters, lambda_2,1({family}) = {minimum}."
    else:
        statement = (
            f"For tested parameters, lambda_2,1({family}) appears to remain in "
            f"the interval [{minimum}, {maximum}]."
        )
    if len(optimal) >= 10 and frame["status"].eq("OPT").all():
        statement += " This describes the observed finite sample; check existing theorems before proposing novelty."
    else:
        statement += " More OPT instances are needed before generalizing it."
    return statement


def analyze() -> str:
    frame = _load_results()
    sections = [
        "L(2,1)-LABELING PRODUCT BENCHMARK ANALYSIS",
        "Statuses are read from the source CSV; no independent optimality audit is implied.",
        f"Input: {INPUT}",
        f"Rows: {len(frame)}; OPT: {(frame['status'] == 'OPT').sum()}; "
        f"non-OPT: {(frame['status'] != 'OPT').sum()}",
    ]
    for family, family_frame in frame.groupby("family", sort=True):
        optimal = family_frame[family_frame["status"] == "OPT"].dropna(subset=["lambda"])
        sections.extend(
            [
                "",
                f"=== {family} ===",
                f"Instances: {len(family_frame)}; OPT rows: {len(optimal)}",
                "Pivot table (cell = lambda [status]):",
                _pivot_text(family_frame),
                "Formula or periodicity check:",
                _linear_summary(optimal),
                "Suggested mathematical conjecture:",
                _conjecture(family, family_frame, optimal),
            ]
        )
    return "\n".join(sections) + "\n"


def main() -> None:
    import argparse
    global INPUT, OUTPUT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=INPUT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    INPUT, OUTPUT = args.input, args.output
    try:
        report = analyze()
    except (OSError, ValueError, KeyError) as error:
        print(f"Analysis failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(report, encoding="utf-8")
    print(report, end="")
    print(f"\nSaved summary to {OUTPUT}")


if __name__ == "__main__":
    main()
