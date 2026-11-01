# Phase 3E.2 — Targeted Telemetry Feasibility Audit

## Audit status

Complete and read-only. The installed `.venv-1` environment was inspected
statically; no solver object was created and no SAT, GA, ILP, benchmark, native
compilation, or package installation was performed. Existing Phase 3E `_02`
artifacts were not edited.

The environment contains Python 3.13.7, `python-sat` 1.9.dev15, and the
`Cadical195` PySAT wrapper for CaDiCaL 1.9.5. The native extension contains
the expected CaDiCaL195 statistics and IPASIR-UP entry points.

## Existing passive telemetry

The current passive interface is sufficient for aggregate solver behavior:

- Boolean result: SAT, UNSAT, or UNKNOWN through `solve()`/`solve_limited()`.
- Cumulative `accum_stats()`: restarts, conflicts, decisions, propagations.
- Per-call and cumulative oracle timing through `time()` and `time_accum()`
  when `use_timer=True`.
- Formula size through the existing encoding/profile artifacts.

The API does not expose internal variable activities, learned-clause events,
unobserved branch-variable identities, or a supported per-variable decision
trace. Consequently, passive metrics cannot test the Phase 3E.1 selector
versus shared-threshold branching hypotheses directly.

## IPASIR-UP feasibility

`Cadical195` exposes connection, active/passive mode, observation,
observation-reset, and decision-classification methods. The installed
`Propagator` interface supplies assignment, decision-level, backtrack, model,
propagation, reason, and optional external-clause callbacks.

This is not transparent instrumentation. A propagator callback introduces
Python crossings and assignment bookkeeping. Observing variables changes what
the backend must preserve for the propagator and may affect preprocessing or
inprocessing. `is_decision()` is meaningful only for currently observed
literals. Passive mode limits propagator activity but does not restore an
observation-free execution path. These risks make the telemetry sampled and
diagnostic, not canonical performance data.

No documented installed wrapper method was found for a native CaDiCaL event
trace or internal activity dump. A native instrumentation project would be
needed for unperturbed full-resolution branching telemetry.

## Decision

**Outcome B — only intrusive or sampled telemetry exists; recommend a
perturbation pilot.**

The recommended pilot is deliberately narrow: the existing ER-60 graph,
`U=112` and `U=127`, fresh processes, matched repetitions, and a stratified
sample of at most 1% of variables. It must include an uninstrumented baseline
and a connected-but-unobserved no-op control before interpreting observed
variables. Exact samples, callback counts, lifecycle operations, and all
passive counters must be retained.

No production integration is authorized by this audit.

## Evidence and limitations

Evidence is recorded in `telemetry_api_inventory.csv`,
`telemetry_option_comparison.csv`, and
`ipasir_up_perturbation_analysis.md`. Source locations are pinned to the
installed wrapper and engine files in the manifest.

The audit did not execute the interface, so callback ordering, quantitative
overhead, and the magnitude of observation-induced preprocessing changes remain
empirical questions. The next pilot must therefore have explicit result,
formula-identity, no-op-control, and lifecycle stop criteria. Existing
aggregate Phase 3E conclusions remain authoritative until such a pilot is
completed.
