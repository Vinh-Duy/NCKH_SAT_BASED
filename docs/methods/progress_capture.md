# Progress capture under an external deadline

## Purpose and experimental scope

`isolated-progress-v2` repairs a measurement limitation in the paired runner.
The archived `isolated-wall-v1` runner transmitted its shared initial greedy
labeling and elementary lower bound, then its final result. Killing a worker
before that final response could discard intermediate solver improvements.
Equal fallback intervals therefore did not establish equal native solver quality.

The v2 confirmation retains the same 39 graphs, three parameter pairs
(1,1), (2,1), (3,2), three repetitions, two backends, and 30-second external
budget: 702 observations on 117 graph/parameter instances. No graph family is
added and no difficult instance is removed. The new measurements remain separate
from the completed confirmation. This change is an instrumentation correction,
not a claimed new labeling algorithm or an established speed improvement.

## Solver adapters

- **SAT:** after each completed SAT/UNSAT span decision, publish an independent
  `SatResult` snapshot. A SAT witness can decrease the feasible upper bound;
  UNSAT at span s can raise the lower bound to s+1. Unknown or interrupted SAT
  calls never raise the bound. The callback retains original vertex identifiers.
  Progress inside an unfinished native SAT call remains unavailable.
- **Assignment/Gurobi:** obtain candidate integer labelings at MIPSOL callbacks
  and dual bounds at MIP/MIPSOL callbacks. Decode and validate labelings before
  retaining them. Normalize their minimum label to zero. Publish improvements
  or changes in certification, rather than every callback. Round finite dual
  bounds down with `floor`; ignore infinity/sentinel values. This deliberately
  avoids strengthening a fractional bound through nearest-integer rounding.
  A weaker later bound cannot replace a stronger retained bound. Inspect the
  final solution/bound as well, including when a native time limit is reached.
- **Failures:** callback exceptions terminate optimization and become errors;
  backend/license failures are never converted to successful greedy results.

The Gurobi adapter follows the official [callback codes](https://docs.gurobi.com/projects/optimizer/en/current/reference/numericcodes/callbacks.html)
and [cbGetSolution API](https://docs.gurobi.com/projects/optimizer/en/current/reference/python/model.html#Model.cbGetSolution).
These are numerical solver bounds under Gurobi's tolerances, not independently
verified proof certificates. Feasibility is checked separately in integer labels.
CPLEX and Big-M remain available through the legacy solver API; the v2 paired
runner supports only CaDiCaL and assignment/Gurobi. It does not silently mix
backends with and without intermediate capture.

## Parent process and timing

Each observation starts a fresh worker. The wall clock starts before process
startup and includes preprocessing, imports/licensing, model construction,
callbacks, transport, validation, and cleanup. The parent accepts only messages
received by its deadline, validates each witness and interval, and rejects
regressions or an OPT claim with unequal bounds. It retains the last accepted
snapshot if the worker is terminated. A failure after an incumbent is received
remains an error rather than being hidden behind that incumbent.

Receipt timestamps are elapsed parent wall time, not solver discovery times.
Cleanup can make total wall time slightly exceed the limit. An OPT snapshot
received before the deadline remains a valid recorded certificate, but coverage
and timing summaries conservatively require total wall time within budget,
matching the historical analysis. A killed worker's peak RSS is unavailable.
SAT counters cover completed span attempts; counters for an interrupted attempt
are not inferred. `Stats_Complete` requires a normal final SAT return with OPT.

## Additional fields

| Field | Meaning |
|---|---|
| `Incumbent_Source` | `greedy`, `sat`, or `gurobi_incumbent`; identifies the retained labeling |
| `LB_Source` | `elementary`, `sat_unsat`, `gurobi_dual`, or `gurobi_optimal` |
| `Progress_Updates` | Number of accepted progress messages, excluding initial/final messages; includes certification changes |
| `Last_Progress_Seconds` | Parent receipt time of the last progress message; blank if none |
| Witness `progress_trace` | Ordered initial/progress/final interval snapshots, statuses, sources, and receipt times |

The final labeling is saved in the witness sidecar. Intermediate labelings are
validated when received, but only their interval/provenance summaries are kept
in the ledger. This ledger is not a replayable UNSAT proof trace.

## Completed confirmation

The complete `general_progress_v2_20261007T062406751526Z.csv` has been audited.
The interrupted `043750933380Z` attempt is excluded. See the [reviewed results](../../paper/generated/progress_confirmation/4927a34577a0c9d4/README.md).
No new solver run is needed to reproduce the present tables; use `make progress-data`.
The commands below describe how the dataset was produced and would start a new run.

## Execution and analysis

```bash
.venv-1/bin/python scripts/run_progress_confirmation.py --plan-only
.venv-1/bin/python scripts/run_progress_confirmation.py
```

The launcher generates a fresh `results/runs/general_progress_v2_<UTC>.csv`,
checks backend availability, executes the fixed cohort, and then audits it.
The maximum allocated observation budget is **5.85 hours**, plus preflight,
cleanup, and analysis overhead; actual completion can be substantially earlier.
Do not change source code or the environment during a run. To resume an
interrupted v2 run, supply its actual CSV path with `--resume`; the writer checks
source, schema, configuration, and environment before accepting prior records.
Do not resume a v1 run or delete its surviving sidecars.

After completion, the launcher prints the versioned report directory under
`results/analysis/progress_confirmation/`. It contains `observations.csv`,
`instances.csv`, `coverage.csv`, `paired_bounds.csv`, `summary.csv`, a README,
and input/output hashes. The audit checks all witnesses against shortest-path
constraints, reference bounds, repetitions, paired consistency, and the progress
ledger. It rejects incomplete or unavailable-backend datasets. A standalone
analysis can be repeated with `scripts/summarize_progress_run.py --input <CSV>`.

A larger LB and a smaller UB are improvements. Pairwise deltas are SAT minus
ILP. Report coverage and interval quality together; do not infer statistical
equivalence from small differences without defining and justifying a criterion.
Repeated timings are not independent graph samples. New timings cannot be
pooled with v1 because callback/transport overhead and capture semantics changed.
The manuscript is not automatically populated with unchecked new findings.

## Historical manuscript builds

`make confirmation` and `make manuscript` verify the frozen v1 bounds report's
input/output hashes through `make bounds-verify`. They do not reconstruct the old
capture audit using changed solver code. `make bounds-data` retains its strict
historical source check and requires the matching old checkout. Raw v1 CSVs,
metadata, witnesses, and report manifests remain unchanged.
