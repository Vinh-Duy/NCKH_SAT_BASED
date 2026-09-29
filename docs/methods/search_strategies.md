# Span search

SAT solves L(h,k) using lower bound h+(Δ−1)min(h,k) when the graph has an edge, or 0 otherwise. For the default L(2,1), this is Δ+1. Δ is the maximum degree; this initial bound need not equal the recorded final LB. The upper bound is the span of a validated greedy labeling.

The invariant is `lower <= optimum <= best.span`. Linear search tests `best.span - 1`; hybrid search tests the midpoint. SAT decreases the upper bound to the decoded labeling's actual span; UNSAT at s raises the lower bound to s+1. OPT is recorded only when the bounds meet. There is no need to repeat s-1 if previous trials already establish optimality. This is not incremental SAT: each span creates a fresh CNF/solver.

A finite timeout runs the entire search phase in a child process, sending the incumbent and bounds to the parent after each call. At the deadline, the latest received incumbent is retained; interruption is not UNSAT. Parent preprocessing and cleanup can exceed the threshold. `timeout_sec=None` runs directly without a child process.

`benchmark_sat_vs_ilp.py` instead wraps each entire run in a worker with an external deadline and records `Wall_Time`; do not substitute the API timeout description for that comparison protocol. See [solver evaluation](../experiments/solver_evaluation.md).

`runtime` measures wall-clock API time. `upper_bound` is the initial greedy bound; `proven_lower_bound` is the final bound; `model_span` is the span used to construct the CNF that produced the saved solution. Counts are absent if SAT has not replaced the greedy incumbent.

SAT/UNSAT history records solver decisions, not an independently checkable proof trace. DRAT/LRAT proofs are not exported.
