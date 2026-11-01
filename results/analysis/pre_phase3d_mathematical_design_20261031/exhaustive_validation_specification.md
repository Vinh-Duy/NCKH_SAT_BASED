# Independent Exhaustive Validation Specification

## Oracle

For each `U`, `g`, and pair of labels `(a,b)` in `{0,...,U}²`, the independent
oracle is the arithmetic predicate `abs(a-b) >= g`. It does not call either
CNF encoder or a SAT solver.

## Threshold extension enumeration

For each label `a`, construct the unique monotone threshold assignment:

`T[t] = (t <= a)` for `t=1,...,U`.

For each `(a,b)`, evaluate both selector values directly against every expanded
candidate clause, using sentinel constants. Record whether at least one selector
value satisfies all clauses. Assert this equals `abs(a-b) >= g`.

Pseudocode:

```text
for U in [1,2,3,4,5]:
  for g in [1,...,U] plus [U+1]:
    for a in [0,...,U]:
      for b in [0,...,U]:
        reference = abs(a-b) >= g
        threshold = lambda(v,t): true if t == 0 else false if t > U else t <= label[v]
        candidate = false
        for s in [false,true]:
          if every t in [0,...,U]:
             (not s or not threshold(u,t) or threshold(v,t+g)) and
             (s or not threshold(v,t) or threshold(u,t+g)):
            candidate = true
        assert candidate == reference
```

The matrix covers equal labels, both boundaries, differences `g-1`, `g`, and
`g+1` whenever those values exist, plus every other label pair.

## Complete-model follow-up

After pair validation, independently enumerate all labelings of small graphs
and compare:

1. reference arithmetic constraints;
2. reference CNF decoded assignments;
3. candidate threshold/selector extensions.

Use paths, cycles, a small complete bipartite graph, and a disconnected graph.
Include fixed-root and incremental upper-bound assumptions. Symmetry must be
tested only after its candidate clause schema is independently specified.

## Acceptance criteria

- Every pair case passes for all listed `U,g`.
- `g>U` has no satisfying selector extension.
- Candidate threshold assignments are monotone and decode to the original label.
- Complete-model label sets agree on small graphs.
- No candidate assignment violates a reference edge or distance-two relation.
