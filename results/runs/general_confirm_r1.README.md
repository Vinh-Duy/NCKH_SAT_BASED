# general_confirm_r1 — SAT–ILP confirmation with three repetitions

**Timeout-capture limitation:** the follow-up [provenance audit](../analysis/unresolved_bounds/README.md)
shows that all 186 FEASIBLE observations retained the shared initial snapshot
after an external wall timeout. These bounds and labels are valid, but do not
record intermediate native solver progress. Equal bounds on unresolved cases
must not be interpreted as equivalent solver effectiveness.

39 graphs × three pairs (1,1), (2,1), (3,2) × three repetitions × two backends = **702 observations**, representing 117 graph/h/k instances. The general-pilot-v1 cohort contains nine trees, three grids, 18 ER graphs (p=0.15 and 0.30), and nine BA graphs (m=2). Graph seeds are 0,1,2 where applicable. Repeat=0,1,2 identifies three runs of the same graph/h/k, not new graphs. Each backend has a 30-second wall budget; CaDiCaL uses order encoding and Gurobi one-thread assignment; symmetry is disabled.

Column definitions follow the [pilot guide](general_pilot_v1.README.md), but repetition and row counts differ. Do not use the one-repetition pilot auditor for this file. The matching metadata records the actual run configuration/environment; do not replace it with the later analysis environment.

From the repository root, run **`make confirmation`** to validate and build the report. Do not rerun or resume this completed benchmark. `scripts/build_confirmation_report.py` checks all 702 witnesses, sample domains, graphs, labels, bounds, and consistency across backends and repetitions. Outputs: [analysis/general_confirm_r1](../analysis/general_confirm_r1/README.md).

Completed data contain 232 OPT + 119 FEASIBLE CaDiCaL observations and 284 OPT + 67 FEASIBLE Gurobi observations. These are **run counts**. Requiring OPT in all three repetitions gives 77 CaDiCaL instances, 94 Gurobi instances, and 76 common instances. FEASIBLE remains an upper bound and is not converted to OPT during aggregation. Valid labels and agreement across solvers/repetitions are not independent UNSAT-certificate verification.
