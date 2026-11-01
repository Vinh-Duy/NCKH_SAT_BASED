# Phase 3E.2 Follow-up — IPASIR-UP Instrumentation Perturbation Pilot

## Purpose and scope

This isolated pilot tested whether sampled IPASIR-UP assignment telemetry is
informative enough to investigate Reference versus Threshold behavior, and
measured the perturbation introduced by connecting and observing variables.
It used only the canonical ER-60 `p=0.30, seed=100` graph, fingerprint
`874baef4edb348567f4083e3d455778a2c87298972c4941b4da331de07baf99c`,
`(h,k)=(3,2)`, `U=112`, and the Phase 3D Reference and Threshold formulas.

Formula preflight passed:

- Reference: 6,720 variables, 715,129 clauses, 2,831,028 literals,
  fingerprint `9b80dd0e1b3a2a5e25fcd1491fe8d1845d07ed25181a614434a8593a782ed166`.
- Threshold: 8,485 variables, 405,550 clauses, 1,198,376 literals,
  fingerprint `74703098b7e6d48ab4ec2cc913fc8bfe3c24763318a602aa6ff4648eddef9d26`.

The installed environment was Python 3.13.7, PySAT 1.9.dev15, and
CaDiCaL195 defaults. Workers were fresh, sequential, and parent-watched at
60 seconds. No conflict budget, solver tuning, GA, ILP, dependency
installation, production change, or prior-artifact modification occurred.

## Matrix and stop gate

The planned matrix was 24 runs: two encodings, modes A-D, and three
repetitions. Mode A was uninstrumented; Mode B connected a no-op propagator
with zero observed variables; Mode C observed a deterministic SHA-256-ranked
1% semantic sample; Mode D would have observed 5%.

The protocol stopped after six runs in the first balanced block:

1. Reference A — SAT, independently valid witness.
2. Threshold A — SAT, independently valid witness.
3. Reference B — SAT, independently valid witness.
4. Threshold B — SAT, independently valid witness.
5. Reference C — SAT, independently valid witness.
6. Threshold C — parent timeout at 60 seconds.

Because an instrumented Candidate run timed out while its baseline succeeded,
the pilot did not run further repetitions or Mode D. The incomplete matrix is
recorded explicitly in `run_manifest.json`; no timeout is classified as
UNKNOWN or UNSAT.

## Perturbation findings

Mode B is not a transparent control. Reference solve time increased from
37.006 s to 52.164 s, approximately 1.41x. Threshold solve time increased
from 40.373 s to 56.929 s, approximately 1.41x. Exposed counters also
changed. This exceeds the pre-registered 10% material-change gate.

The completed Reference Mode C run took 53.595 s, approximately 1.45x its
baseline. It observed 67 of 6,720 one-hot label variables (0.997%) and
recorded 306,477 assignment events: 5,807 decisions and 300,670
propagations. The Candidate Mode C worker timed out before producing final
statistics. Higher sampling was not attempted.

These are paired operational observations, not statistical estimates. Three
repetitions were not completed, and no claim is made about general solver
performance.

## Telemetry quality and witness validation

The installed callback contract was verified from `pysat.engines.Propagator`.
Callbacks returned no-op values: empty lists for propagation, reasons, and
clauses; `check_model()` returned `True`. The callback performed no I/O,
solver mutation, external reasoning, or termination. Decision classification
used `Cadical195.is_decision(lit)` only within `on_assignment`.

All five completed SAT runs had independently valid witnesses. The candidate
timeout is recorded as `PARENT_TIMEOUT` with unavailable solver counters as
null. The sampled counts apply only to observed variables and were not
extrapolated.

## Final decision

**Decision B — telemetry is useful but materially intrusive.**

The Reference sampled run demonstrates that observed assignment events can be
classified into decisions and propagations by semantic category. However, the
connected zero-observation control already changes runtime materially, and
the first Candidate sampled run reaches the parent timeout. Observed
variables can affect inprocessing, while Python callbacks add overhead.

Retain the passive Phase 3E statistics as the authoritative performance
evidence. Treat IPASIR-UP results as exploratory instrument validation only.
Do not use them as ordinary solver-performance data, do not extrapolate them
to all variables, and do not automatically authorize further telemetry runs
or production integration.

## Limitations

The stopped pilot cannot estimate repetition variability, compare all three
operational blocks, or measure the 5% condition. Backtrack callbacks provide
levels rather than exact undone-variable sets. The API exposes no unobserved
branch-variable trace or native activity trace. The failed initial runner
attempt and corrected bounded pilot are preserved as separate numbered
artifacts.
