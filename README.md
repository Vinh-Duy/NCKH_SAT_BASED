# SAT-Based L(h,k)-Labeling

This project uses the PySAT toolkit to study the graph labeling problem
$L(h,k)$ with an order-encoded CNF model. The default configuration is the
$L(2,1)$-labeling problem:

- Adjacent vertices must receive labels whose difference is at least $2$.
- Vertices at graph distance two must receive different labels.
- The **span** is the smallest value $s$ for which a valid labeling exists.

The project includes exact SAT experiments, benchmark generation, and a
visualization of label assignments on path graphs.

## Project Files

| File | Description |
| --- | --- |
| `bai_tap_L21.py` | Builds the CNF model and solves paths $P_n$ for $n=3,\ldots,10$. |
| `visual.py` | Solves and displays an $L(2,1)$ labeling for a path graph. |
| `benchmark.py` | Runs benchmarks for cycle graphs $C_n$, complete graphs $K_n$, and hypercubes $Q_n$. |
| `benchmark_q_extended.py` | Runs a focused $Q_n$ benchmark with exact SAT results for small dimensions and fast estimates for larger dimensions. |
| `benchmark_cadical195.py` | Runs the same SAT model with CaDiCaL 1.95 and writes separate comparison results. |
| `benchmark_q_extended_cadical195.py` | Runs the extended $Q_n$ benchmark with CaDiCaL 1.95 and separate results. |
| `results/` | Benchmark results in CSV and Excel formats. |
| `logs/` | Captured benchmark output and runtime logs. |

## Requirements

- Python 3.8 or newer
- `python-sat` (PySAT and the Glucose3 solver)
- `networkx`
- `matplotlib`
- `openpyxl`

Install the dependencies directly:

```bash
python3 -m pip install python-sat networkx matplotlib openpyxl
```

Using a virtual environment is recommended:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install python-sat networkx matplotlib openpyxl
```

## Quick Start

Solve the sample path graphs:

```bash
python3 bai_tap_L21.py
```

Display a labeling for the path configured in `visual.py`:

```bash
python3 visual.py
```

The visualization opens a Matplotlib window and prints the selected span and
the label assigned to each vertex.

## Run the Main Benchmark

Run the complete benchmark suite with:

```bash
python3 benchmark.py
```

The script benchmarks $C_n$ and $K_n$ for $n=3,\ldots,50$, and $Q_n$ for
$n=2,\ldots,50$. SAT is used for the smaller hypercubes; larger hypercubes use
the greedy estimate implemented in the script so that the experiment does not
attempt to construct graphs with an impractically large number of vertices.

The benchmark writes:

- `results/ket_qua_C.csv` and `results/ket_qua_C.xlsx` for cycle graphs.
- `results/ket_qua_K.csv` and `results/ket_qua_K.xlsx` for complete graphs.
- `results/ket_qua_Q.csv` and `results/ket_qua_Q.xlsx` for hypercubes.
- `logs/benchmark_run.log` for console output captured during the run.

The full benchmark can take a substantial amount of time, especially for
larger complete graphs and hypercubes.

## Run the Extended Hypercube Benchmark

The focused benchmark accepts command-line options:

```bash
python3 benchmark_q_extended.py
```

Available options:

```text
--first N         First hypercube dimension (default: 11)
--last N          Last hypercube dimension (default: 50)
--exact-max-n N   Run exact SAT through this dimension (default: 6)
--timeout SEC     SAT timeout per graph (default: 60)
```

For example, to solve dimensions 2 through 8 exactly:

```bash
python3 benchmark_q_extended.py --first 2 --last 8 --exact-max-n 8 --timeout 300
```

This script writes `results/ket_qua_Q_extended.csv` and appends runtime information to
`logs/benchmark_run_q_ext.log`. Rows marked `OPT` are exact SAT results. Rows marked
`FEASIBLE_ESTIMATE` are fast estimates and should not be interpreted as proof
of optimality.

## Run the CaDiCaL 1.95 Benchmark

Run a separate benchmark with CaDiCaL 1.95 so the existing Glucose3 results are
preserved:

```bash
python3 benchmark_cadical195.py
```

The script runs the same `C_n`, `K_n`, and `Q_n` ranges as `benchmark.py`,
through `n=50`, using CaDiCaL 1.95. Results are written to separate
`results/ket_qua_<graph>_cadical195.csv` files, with runtime details in
`logs/benchmark_cadical195.log`.

## Result Columns

Each CSV file contains the following columns:

| Column | Meaning |
| --- | --- |
| `Graph` | Graph name, such as `C_10` or `Q_6`. |
| `n` | Number of vertices. |
| `var` | Number of order-encoding variables. |
| `clause` | Number of generated CNF clauses. |
| `time` | Solver runtime in seconds. |
| `lambda` | Computed span or estimated span. |
| `status` | Usually `OPT`, `TIMEOUT`, `UNSOLVED`, or `FEASIBLE_ESTIMATE`. |

## Implementation Notes

The model represents each label with monotone order variables. For a span
$s$, the encoding creates variables that represent threshold statements such
as $f(v) \leq i$. CNF clauses enforce monotonicity and prevent labels that are
too close for adjacent or distance-two vertex pairs.

The main benchmark searches span values from an upper bound down to a lower
bound. The first satisfiable value found in this descending search is recorded
as the best result for that run. Timeout and estimate statuses are kept in the
output so that they can be distinguished from exact optimal SAT results.

## Troubleshooting

- If Matplotlib does not open a window, check that the active Python
  environment has a graphical backend available.
- If a dependency cannot be imported, activate the virtual environment and
  reinstall the packages with `python3 -m pip`.
- Large benchmark instances can require significant memory and runtime. Use
  `benchmark_q_extended.py` with a smaller `--exact-max-n` when an exact SAT
  run is too expensive.

## License

No license file is currently included in this repository.
