# SAT and ILP Methods for L(h,k)-Labeling

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
| `src/core/graph_utils.py` | Construction of $C_n$, $K_n$, and $Q_n$; graph constraints; bounds; greedy labeling. |
| `src/core/validator.py` | Independent validation of $L(h,k)$ labelings. |
| `src/core/io.py` | Shared CSV writing and benchmark logging. |
| `src/models/sat_encoding.py` | Order encoding, forbidden-label clauses, and symmetry breaking. |
| `src/models/ilp_assignment.py` | Binary assignment formulation and warm-start helpers. |
| `src/solvers/sat_solver.py` | Glucose3/CaDiCaL wrappers with linear and hybrid search. |
| `src/solvers/ilp_solver.py` | Gurobi and CPLEX wrappers for assignment and Big-M formulations. |
| `benchmarks/run_sat.py` | SAT experiments for cycle, complete, and hypercube graphs. |
| `benchmarks/run_ilp.py` | ILP experiments and assignment-versus-Big-M comparison. |

Detailed mathematical documentation is available in:

- [SAT encoding](docs/sat_encoding.md)
- [ILP formulations](docs/ilp_formulations.md)
- [Span search strategies](docs/search_strategies.md)

## Reproducibility

All benchmark runners write results incrementally. The `--family` option accepts
`C`, `K`, `Q`, or `ALL`. Use `--first` and `--last` to select the graph-size
range, and `--timeout` to set the per-instance time limit.

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

Each runner uses the same output schema:

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

## License

No license file is currently included in this repository.
