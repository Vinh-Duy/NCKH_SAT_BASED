# Callback validation

## Installed contract

The pilot used the installed `pysat.engines.Propagator` contract from
`python-sat 1.9.dev15`:

- `on_assignment(lit, fixed=False)` receives observed assignments.
- `on_new_level()` reports a new decision level.
- `on_backtrack(to)` reports the target backtrack level.
- `check_model(model)` returns a boolean.
- `propagate()`, `provide_reason(lit)`, and `add_clause()` return empty lists.

The pilot connected the propagator with `Cadical195.connect_propagator()`,
observed only precomputed variable IDs, and called `is_decision(lit)` inside
`on_assignment`. It never proposed clauses, literals, decisions, conflicts,
assumptions, or termination. It did not write files from callbacks or retain
the complete event stream.

## Observed behavior

Mode B successfully connected the propagator with zero observed variables for
both encodings. Mode C successfully delivered assignment callbacks and
decision/propagation classifications for the completed Reference run. The
Reference Mode C sample recorded 306,477 assignment events, including 5,807
classified decisions and 300,670 classified propagations.

The Candidate Mode C worker exceeded the 60-second parent watchdog and was
terminated before a completed callback summary. It is recorded as
`PARENT_TIMEOUT`, not UNKNOWN or UNSAT.

## Validity limits

`is_decision()` is valid only for a currently observed literal in the callback
context; the counts are therefore sampled observed-variable events, not a
complete branching trace. Backtrack callbacks provide a target level but not
the exact undone-variable set. No assignment counts were extrapolated to
unobserved variables.

The connected and observed modes can alter CaDiCaL inprocessing and execution.
Their metrics are diagnostic instrument measurements, not ordinary
un-instrumented solver performance.
