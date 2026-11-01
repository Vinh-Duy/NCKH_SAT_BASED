# Next telemetry experiment specification

## Purpose

Measure whether a narrowly sampled IPASIR-UP propagator can explain the
reference-versus-threshold solver behavior on the existing ER-60 graph without
being mistaken for production performance.

## Scope

Use only the canonical Phase 3E ER-60 graph and the already validated
reference and threshold formulas at `U=112` and `U=127`. Use fresh processes,
the existing PySAT/CaDiCaL195 versions, the existing solver configuration,
and the existing three repetition blocks. Do not expand the graph cohort.

Run four conditions per encoding/span/repetition:

1. uninstrumented baseline;
2. connected no-op propagator with no observations;
3. observed sample of formula variables, active mode;
4. the same observed sample, passive mode where supported.

The first pilot should sample at most 1% of variables, stratified by reference
label/threshold variables and threshold selectors. Record the exact sample
and use the same IDs in matched conditions. If the no-op condition changes
runtime or counters materially, stop before interpreting observed samples.

## Measurements

Retain all existing formula and solver metrics, plus:

- condition and repetition block;
- observed variable IDs and strata;
- assignment callback count;
- decision callback count obtained only through `is_decision`;
- propagation callback count;
- new-level and backtrack counts;
- callback wall time and callback CPU time if available;
- propagator active/passive state;
- final `accum_stats()` and solver result;
- reset/disconnect lifecycle outcome.

All missing values remain null. No metric is clipped or inferred.

## Controls and stopping criteria

Use a fresh process for every arm. Preserve formula fingerprints and clause
counts. Stop the pilot if any of the following occurs:

- a callback raises or changes the SAT result;
- formula identity differs;
- the connected no-op condition differs materially from baseline;
- a solver lifecycle method leaves the following independent call
  interrupted or otherwise changes its result;
- callback overhead cannot be measured separately;
- the observed condition causes a large or irreproducible change in passive
  counters.

Define material change before execution, for example a result mismatch or a
greater-than-10% change in solve time or exposed counters in the paired
no-op control. The threshold is a pilot gate, not a claim about solver
variability.

## Deliverables

Write raw per-arm JSONL, a manifest containing package/native binary hashes,
the exact observed IDs, and a derived comparison CSV. Keep the pilot separate
from Phase 3E `_02`; it must not replace or amend canonical results.
