# IPASIR-UP perturbation analysis

## Installed interface

The installed `python-sat` distribution is `1.9.dev15`. Its `Cadical195`
wrapper exposes the IPASIR-UP methods `connect_propagator`,
`disconnect_propagator`, `enable_propagator`, `disable_propagator`,
`propagator_active`, `observe`, `ignore`, `reset_observed`, and
`is_decision`. The native extension contains corresponding
`cadical195_pconn`, `pdisconn`, `penable`, `pdisable`, `pactive`, `vobserve`,
`vignore`, `vreset`, and `isdeclit` symbols. This establishes availability,
not behavioral equivalence to an uninstrumented run.

`Propagator.on_assignment(lit, fixed)`, `on_new_level()`, and
`on_backtrack(to)` provide assignment and search-level callbacks. The
`is_decision(lit)` query classifies a currently observed literal as a branch
assignment or propagation. The API does not expose a passive callback for
every internal decision variable without first observing variables.

## Why observation is intrusive

The wrapper documentation says that observed variables are managed by the
external propagator. CaDiCaL's observation interface is intended for
IPASIR-UP reasoning, not passive profiling. Observing variables can prevent
inprocessing elimination or otherwise preserve them for the propagator.
Therefore a run with observed variables is not a transparent measurement of
the production solver. Connecting a propagator also adds Python callback
crossings and assignment bookkeeping.

`disable_propagator()` makes the propagator passive, meaning it is invoked
only for model checks according to the wrapper documentation; it does not
make observation-free execution or restore the original preprocessing path.
`disconnect_propagator()` resets the observed-variable set for subsequent
solver use, but it cannot retroactively remove perturbation from calls already
made.

## Safe experimental use

Use paired fresh processes, with the exact same formula, configuration,
ordering, and repetition identifier:

1. uninstrumented control;
2. propagator connected but no variables observed;
3. a small, pre-registered observed-variable sample;
4. optionally the same sample with the propagator passive.

Compare result, elapsed time, `accum_stats()`, and formula/solver setup
metrics. Continue only if the connected-but-unobserved control is close to
the uninstrumented control and the sampled condition is explicitly labeled
as perturbed. Never merge sampled metrics into the canonical Phase 3E
production comparison.

The pilot must record the exact observed IDs, callback count, callback
duration, propagator active/passive state, and whether `reset_observed()` or
`disconnect_propagator()` was called. A no-op callback is preferable for
initial feasibility testing. Do not use `check_model`, `propagate`,
`provide_reason`, or external clauses in a measurement pilot.

## Not established

No supported installed API was found for internal variable activities,
unobserved branch decisions, clause learning events, or a documented
CaDiCaL trace that provides the requested category-level branching data.
Native instrumentation would be a separate project requiring a pinned source
revision, build recipe, and validation against an uninstrumented binary.
