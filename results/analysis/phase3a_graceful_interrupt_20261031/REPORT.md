# Phase 3A.2 — Graceful In-Process SAT Interruption

## Scope and integrity

This implementation did not run the research cohort and did not modify the
historical benchmark, Phase 1/2 outputs, or the Phase 3A diagnostic pilot.
The benchmark parent timeout remains the final safety fallback. The new
deadline is an absolute monotonic deadline for one method-task, so encoding,
GA preprocessing, validation, logging, and all SAT calls share one budget.
The default shutdown reserve is 1 second and is configurable with
`--shutdown-reserve`.

## Backend API inspection

The installed environment is `.venv-1`, Python 3.13, PySAT 1.9.dev15, with
`pysat.solvers.Cadical195`.

The installed PySAT source was inspected directly:

- `Cadical195.solve(assumptions=[])` invokes the regular CaDiCaL solve call and
  returns `True`, `False`, or `None`.
- `Cadical195.solve_limited(assumptions=[], expect_interrupt=False)` invokes
  `cadical195_solve_lim`, maps the limited result to `True`, `False`, or
  `None`, and is the supported bounded interface.
- `Cadical195.conf_budget(budget)` is implemented.
- `Cadical195.prop_budget(...)` raises `NotImplementedError`.
- `Cadical195.interrupt()` and `Cadical195.clear_interrupt()` both explicitly
  raise `NotImplementedError("Limited solve is currently unsupported by CaDiCaL.")`.
- There is no CaDiCaL195 wall-time API in the installed wrapper.

A deterministic 8-pigeon/7-hole formula was tested with
`conf_budget(1)`. `solve_limited()` returned `None` and
`accum_stats()` returned counters including one or more conflicts. The
following regular solve was not accidentally interrupted, but the
interrupt/reset methods themselves are not usable for CaDiCaL195. Therefore,
no claim is made that an active CaDiCaL195 call can be interrupted safely by
this installed API.

## Implementation

Changed solver behavior is opt-in through an absolute `deadline`:

- `src/solvers/sat_solver.py` checks the deadline before every SAT call.
- A deadline reached before a call returns `UNKNOWN` with
  `unknown_reason=INTERNAL_DEADLINE`; bounds and the verified incumbent are
  unchanged.
- For a backend with a tested, callable interrupt implementation, a watchdog
  requests interruption and a `None` result is treated as internal UNKNOWN.
  Final counters are sampled after the solver returns and deltas are emitted
  only when both snapshots are valid and monotone.
- CaDiCaL195 is explicitly capability-gated out of the watchdog path because
  its exposed interrupt methods are known stubs that raise
  `NotImplementedError`. It remains subject to the parent hard timeout.
- Incremental SAT receives the same deadline across all assumption calls; it
  never starts a fresh per-span timeout.

`benchmarks/benchmark_incremental_sat.py` now:

- reserves 1 second by default from the 30-second parent cap;
- passes one absolute internal deadline into the worker and SAT solver;
- charges `sat_ga_bound` GA preprocessing against that same deadline;
- records internal UNKNOWN separately from parent `INTERRUPTED`;
- retains parent-side post-exit telemetry recovery with null final counters.

Telemetry attempt completion records now include the internal deadline,
remaining budget, and `unknown_reason`. Parent-terminated attempts continue to
use `attempt_terminated_by_parent` and retain null final counters.

## Regression evidence

Focused tests: **31 passed**:

- supported interrupt watchdog returns UNKNOWN and captures final counters;
- UNKNOWN preserves lower/upper bounds and the incumbent witness;
- expired deadlines stop before a new call without changing bounds;
- CaDiCaL bounded UNKNOWN preserves accumulated statistics;
- CaDiCaL interrupt/reset API limitation is asserted explicitly;
- GA preprocessing honors an already-expired shared deadline;
- parent-worker error and parent interruption classifications remain distinct;
- existing tri-state and telemetry recovery tests pass.

Full test suite: **207 passed, 1 skipped**. The skip is the existing
environment-dependent test. `py_compile` passed for all changed Python files,
and `git diff --check` passed.

## Conclusion and remaining limitation

A safe internal UNKNOWN with final counters was demonstrated for a controlled
backend implementing the supported interrupt contract, and a real
CaDiCaL195 `solve_limited()` UNKNOWN with counters was demonstrated.

An active wall-clock interruption of the installed CaDiCaL195 backend was **not
demonstrated**, because the actual PySAT wrapper explicitly does not support
`interrupt()` or `clear_interrupt()`. Consequently, difficult CaDiCaL calls
that exceed the internal deadline can still reach the parent hard timeout and
are correctly recorded as parent `INTERRUPTED`, with null final counters. A
future CaDiCaL upgrade exposing a tested interrupt/reset API can enable the
watchdog path without changing the deadline or tri-state semantics.
