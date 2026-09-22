# SAT and ILP Methods for L(h,k)-Labeling

This project studies the graph labeling problem $L(h,k)$ with SAT and ILP
formulations. The default problem is $L(2,1)$-labeling:

- Adjacent vertices must receive labels whose difference is at least $2$.
- Vertices at graph distance two must receive different labels.
- The **span** is the smallest value $s$ for which a valid labeling exists.

The SAT model uses order encoding and can apply family-specific symmetry
breaking for paths, cycles, and hypercubes. Petersen and product graphs do not
use those assumptions unless they are mathematically justified.

## Requirements

- Python 3.8 or newer
- `python-sat` (PySAT and the Glucose3 solver)
- `networkx`
- `pandas`
- `matplotlib`
- `openpyxl`
- `gurobipy` (Gurobi MILP benchmark)
- `docplex` and the CPLEX Python runtime (CPLEX MILP benchmark)

Install the dependencies directly:

```bash
python3 -m pip install python-sat networkx pandas matplotlib openpyxl gurobipy docplex
```

Using a virtual environment is recommended:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install python-sat networkx pandas matplotlib openpyxl gurobipy docplex
```

## Architecture

The implementation is organized as a reusable Python package:

| Module | Responsibility |
| --- | --- |
| `src/core/graph_utils.py` | Construction of standard graphs, $GP(n,k)$, Cartesian products, and corona products; graph constraints; bounds; greedy labeling. |
| `src/core/validator.py` | Independent validation of $L(h,k)$ labelings. |
| `src/core/io.py` | Shared CSV writing and benchmark logging. |
| `src/models/sat_encoding.py` | Order encoding, forbidden-label clauses, and symmetry breaking. |
| `src/models/ilp_assignment.py` | Binary assignment formulation and warm-start helpers. |
| `src/solvers/sat_solver.py` | Glucose3/CaDiCaL wrappers with linear and hybrid search. |
| `src/solvers/ilp_solver.py` | Gurobi and CPLEX wrappers for assignment and Big-M formulations. |
| `benchmarks/run_sat.py` | SAT experiments for cycle, complete, hypercube, and generalized Petersen graphs. |
| `benchmarks/run_ilp.py` | ILP experiments and assignment-versus-Big-M comparison. |
| `benchmarks/benchmark_petersen.py` | SAT sweep for $GP(n,k)$ with $7 \le n \le 50$. |
| `benchmarks/benchmark_products.py` | SAT sweep for Cartesian and corona product graphs with $3 \le n,m \le 10$. |

Detailed mathematical documentation is available in:

- [SAT encoding](docs/sat_encoding.md)
- [ILP formulations](docs/ilp_formulations.md)
- [Span search strategies](docs/search_strategies.md)
- [Petersen benchmark](docs/petersen_benchmark.md)
- [Product benchmark](docs/products_benchmark.md)
- [Solver evaluation](docs/solver_evaluation.md)

## Reproducibility

All benchmark runners write results incrementally. The `--family` option accepts
`C`, `K`, `Q`, `petersen`, or `ALL`. Use `--first` and `--last` to select the graph-size
range for the first three families, and `--timeout` to set the per-instance time limit.

### SAT experiments

Run the default SAT experiment with Glucose3:

```bash
python3 -m benchmarks.run_sat \
  --family ALL \
  --first 3 \
  --last 20 \
  --solver glucose \
  --strategy hybrid \
  --timeout 60
```

The available SAT solvers are `glucose` and `cadical`. The search strategies
are `linear` and `hybrid`:

```bash
python3 -m benchmarks.run_sat \
  --family Q \
  --first 2 \
  --last 6 \
  --solver cadical \
  --strategy linear \
  --timeout 300 \
  --output results/sat_hypercube.csv
```

Run one generalized Petersen graph with order `n` and jump `k`:

```bash
python3 -m benchmarks.run_sat \
  --family petersen \
  --n 9 \
  --k 2 \
  --solver glucose \
  --strategy hybrid \
  --timeout 60 \
  --output results/sat_petersen_single.csv
```

Run the complete Georges-Mauro sweep (`7 <= n <= 50`, `1 <= k < n/2`):

```bash
python3 benchmarks/benchmark_petersen.py
```

### Product experiments

The product benchmark covers three Cartesian families:

- $C_n \square C_m$
- $C_n \square P_m$
- $P_n \square P_m$

It also covers three corona families:

- $C_n \circ C_m$
- $P_n \circ P_m$
- $C_n \circ P_m$

The graph constructors normalize NetworkX tuple vertices to consecutive
integer labels before the graph reaches the SAT or ILP encoding. The benchmark
scans all $n,m \in [3,10]$, for 384 instances in total, using Glucose and the
hybrid SAT search with a 60-second limit per instance:

```bash
./.venv-1/bin/python benchmarks/benchmark_products.py
```

Results are written to `results/products_benchmark.csv` and
`logs/benchmark_products.log`. The product CSV has the fields `Graph`, `V`,
`E`, `lambda`, `time`, and `status`.

### ILP experiments

Run the binary-assignment ILP formulation with Gurobi:

```bash
python3 benchmarks/run_ilp.py \
  --family ALL \
  --first 3 \
  --last 10 \
  --solver gurobi \
  --formulation assignment \
  --timeout 60
```

The available ILP solvers are `gurobi` and `cplex`. The assignment formulation
uses binary variables $x_{v,k}$, a span variable, greedy warm starts, and
independent labeling validation. The `big-m` formulation is available for
comparison; `both` writes one result for each formulation:

```bash
python3 benchmarks/run_ilp.py \
  --family C \
  --first 3 \
  --last 20 \
  --solver gurobi \
  --formulation both \
  --timeout 300 \
  --output results/ilp_comparison.csv
```

The ILP runner also accepts `--family petersen --n <n> --k <k>`.

Gurobi requires an active installation and license. CPLEX requires both the
`docplex` package and an accessible CPLEX runtime and license.

## Result Status

- `OPT`: the solver proved optimality.
- `FEASIBLE`: a valid labeling was found, but optimality was not proved before
  the time limit.
- `TIMEOUT`: no solver solution was available when the time limit was reached.
- `UNAVAILABLE`: the selected optimization backend could not be started, for
  example because its runtime is not installed.
- `INVALID`: a returned labeling failed independent validation.

## CSV Schema

The standard SAT and ILP runners use the following schema:

| Column | Meaning |
| --- | --- |
| `Graph` | Graph identifier, such as `C_10`, `K_8`, or `Q_4`. |
| `n` | Number of vertices in the graph. |
| `var` | Number of solver variables. |
| `clause/constr` | Number of SAT clauses or ILP constraints. |
| `time` | Solver runtime in seconds. |
| `lambda` | Computed span, or empty when no labeling was returned. |
| `UB` | Greedy upper bound or the current feasible upper-bound record. |
| `status` | Solver and validation status. |

The dedicated product benchmark uses a smaller schema focused on graph size
and experiment tracking: `Graph`, `V`, `E`, `lambda`, `time`, and `status`.

## License

No license file is currently included in this repository.
