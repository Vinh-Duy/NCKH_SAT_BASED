# SAT-Based L(h,k)-Labeling

This project uses the PySAT toolkit to study the graph labeling problem
$L(h,k)$ with an order-encoded CNF model. The default configuration is the
$L(2,1)$-labeling problem:

- Adjacent vertices must receive labels whose difference is at least $2$.
- Vertices at graph distance two must receive different labels.
- The **span** is the smallest value $s$ for which a valid labeling exists.

The shared CNF builder also supports symmetry breaking. Path instances impose
$f(0) < f(n-1)$, cycle instances fix vertex 0 to label 0 and order its two
neighbors, and hypercube instances fix vertex 0 to label 0 and order the
neighbors corresponding to the cube dimensions. These constraints preserve
SAT/UNSAT status while removing equivalent labelings from the search. Complete
graphs keep the unrestricted encoding because these family-specific rules do
not apply to them.

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
| `benchmark_hybrid.py` | Runs one combined C/K/Q benchmark using binary bound reduction followed by sequential proof search. |
| `plot_results.py` | Reads hybrid benchmark results and plots lambda growth for C, K, and Q graphs. |
| `validation.py` | Validates a span and vertex labeling against the $L(h,k)$ constraints. |
| `results/` | Benchmark results in CSV and Excel formats. |
| `logs/` | Captured benchmark output and runtime logs. |

## Requirements

- Python 3.8 or newer
- `python-sat` (PySAT and the Glucose3 solver)
- `networkx`
- `pandas`
- `matplotlib`
- `openpyxl`

Install the dependencies directly:

```bash
python3 -m pip install python-sat networkx pandas matplotlib openpyxl
```

Using a virtual environment is recommended:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install python-sat networkx pandas matplotlib openpyxl
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

## Plot Hybrid Results

After generating `results/ket_qua_hybrid.csv`, create a three-panel plot for
cycle, complete, and hypercube graphs:

```bash
python3 plot_results.py
```

The script filters rows without a numeric `lambda` value and rows with
`status=INVALID`. The output is saved to:

```text
results/bieu_do_lambda.png
```

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

During development, exact instances use a 60-second per-graph timeout by
default. To run a final report with a larger budget, pass `--timeout` in
seconds, typically 600 or 900:

```bash
python3 benchmark.py --timeout 600
python3 benchmark_cadical195.py --timeout 900
```

Timed-out instances with a valid SAT result are marked `FEASIBLE`; instances
without a SAT result are marked `FEASIBLE_ESTIMATE`. Their `UB` column records
the tested bounds followed by the estimate used as fallback.

## Run the Hybrid Benchmark

The hybrid benchmark writes C, K, and Q results to one CSV file. It first uses
binary search to reduce a feasible upper bound, then checks smaller bounds
sequentially until `UNSAT` proves the previous `SAT` bound optimal. The `UB`
column records the complete tested history, including the search phase:

```text
B8:UNSAT -> B12:SAT -> S11:UNSAT
```

The binary phase uses solver budgets for each bound. The final sequential
check is limited to the candidate immediately below the binary result. `OPT`
is emitted only after an UNSAT proof or a proven mathematical lower bound; a
budget interruption produces `FEASIBLE` or `TIMEOUT`, never `OPT`.

Run the complete combined benchmark with:

```bash
python3 benchmark_hybrid.py
```

Output:

```text
results/ket_qua_hybrid.csv
```

For a smaller run, for example:

```bash
python3 benchmark_hybrid.py --family ALL --first 3 --last 10 --exact-max-q 5
```

`OPT` means the binary result passed the final sequential UNSAT check.
`FEASIBLE` means a valid labeling was found but proof was interrupted. Q dimensions above
`--exact-max-q` are marked `FEASIBLE_ESTIMATE` and are not exact SAT results.

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

The timeout is enforced inside each SAT call with the solver conflict budget,
not only between successive span values. This keeps the 60-second development
run responsive while allowing 10-15 minute budgets for final measurements.

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
| `UB` | Full tested upper-bound history, for example `8 -> 7 -> 6 -> 5`. For `OPT`, the last SAT bound is `lambda`; for `FEASIBLE`, it is not proven optimal. |
| `status` | Usually `OPT`, `TIMEOUT`, `UNSOLVED`, or `FEASIBLE_ESTIMATE`. |

## Validate a Labeling

Use `validate_labeling` to check an instance independently from the SAT solver.
The span `m` is an upper bound, so labels must be integers in `0..m`.

Run the following command from the project directory to validate one known
labeling manually:

```bash
python3 -c "from validation import validate_labeling; print(validate_labeling(3, [(0,1),(1,2),(0,2)], [], 4, {0:0,1:2,2:4}, h=2, k=1))"
```

Expected output:

```text
(True, [])
```

The result is a pair `(valid, errors)`. `True` and an empty error list mean
that `m` and `L` satisfy all constraints. To test an invalid labeling, change
`{0:0,1:2,2:4}` to `{0:0,1:1,2:4}`. The validator will return `False` and
describe the violated edge constraint.

```python
from validation import validate_labeling

valid, errors = validate_labeling(
  n_vertices=3,
  edges=[(0, 1), (1, 2), (0, 2)],
  dist2_pairs=[],
  span=4,
  labels={0: 0, 1: 2, 2: 4},
  h=2,
  k=1,
)
print(valid)   # True
print(errors)  # []
```

The benchmark scripts decode each SAT model into `L` and run this validation
before recording an `OPT` result. A failed check is logged and is not accepted
as a valid result.

To run a real SAT result through the validator, use this small C3 benchmark:

```bash
python3 -c "import networkx as nx; from benchmark_cadical195 import run_benchmark; print(run_benchmark('C_3', nx.cycle_graph(3), timeout_sec=10))"
```

The output should contain `lambda: 4` and `status: 'OPT'`. For the complete
benchmark, run:

```bash
python3 benchmark_cadical195.py
```

Each SAT model found by the benchmark is decoded into `L`, validated, and only
then written to the result CSV.

## Implementation Notes

The model represents each label with monotone order variables. For a span
$s$, the encoding creates variables that represent threshold statements such
as $f(v) \leq i$. CNF clauses enforce monotonicity and prevent labels that are
too close for adjacent or distance-two vertex pairs.

The benchmark starts from a feasible upper bound and tests span values in
descending order. Each SAT result lowers the current upper bound and the next
smaller span is tested. The first UNSAT after a SAT result proves the previous
span is optimal. If a timeout occurs after a feasible result, the row is marked
`FEASIBLE` rather than `OPT`; estimate statuses are also kept separate from
exact SAT results.

The `UB` column stores every tested bound in order, including the bound that
returned `UNSAT` or the bound being tested when a timeout occurred.

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
