# Phase 3A.3 Conflict-Budget Design

The optional `task_conflict_budget` is one positive integer per method-task.
It is owned by a search-level `ConflictBudget` tracker, not by a solver
object. Before every limited SAT call, the tracker configures the next call
with its current positive remaining conflicts. After the call, cumulative
backend conflict counters are sampled and the monotone delta is added to the
tracker.

The same tracker is passed through:

- original SAT span rebuilds;
- incremental SAT assumption calls;
- GA-bound SAT after GA preprocessing.

If counters are missing, invalid, or decrease, accounting stops with UNKNOWN
and an explicit accounting reason. No zero default is used. A `None` result
is UNKNOWN; only a demonstrably exhausted configured call is classified as
`CONFLICT_BUDGET`. The incumbent and lower/upper bounds are preserved.

The ordinary `solve()` path remains unchanged when no task conflict budget is
provided. The end-to-end monotonic deadline and parent hard timeout remain
separate safety controls. Conflict counts are SAT-search resources and are not
treated as seconds.
