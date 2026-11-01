# Distance-2 Execution Map

## Discovery path

1. `solve_graph()` calls `graph_constraints(normalized)` in
   `src/solvers/sat_solver.py:892`.
2. `graph_constraints()` in `src/core/graph_utils.py:123-137`:
   - validates the graph;
   - copies `graph.edges()`;
   - computes `nx.all_pairs_shortest_path_length(graph, cutoff=2)`;
   - iterates the graph's node list with `nodes[index + 1:]`;
   - keeps only pairs whose shortest distance is exactly 2.
3. This representation is unordered by construction: `(u,v)` is emitted only when
   `u` occurs before `v` in the node list. It does not enumerate common neighbors
   or two-edge paths, so multiple common neighbors do not create repeated pair
   events.
4. The resulting list is passed through `_search()` / `_search_incremental()` to
   `_solve_span()` / `build_cnf()` in `src/solvers/sat_solver.py:207-258` and
   `538-589`.

## Clause path

`build_cnf()` in `src/models/sat_encoding.py:297-330` creates `OrderVars`, emits
monotonicity and symmetry clauses, then loops over `distance_two_pairs` and calls
`forbid_close_labels(..., k)` once per pair.

`forbid_close_labels()` in `src/models/sat_encoding.py:131-158`:

- returns no clauses when the gap is non-positive;
- otherwise handles fixed-label endpoints through `_fixed_close_label_clauses()`;
- for free endpoints, loops over every `first_label` in `0..U` and every
  `second_label` whose absolute difference is less than `k`;
- emits the concatenation of `not_equal_literals(first, first_label)` and
  `not_equal_literals(second, second_label)`.

`not_equal_literals()` in `src/models/sat_encoding.py:126-134` translates
`f(v) != label` into order literals. With no fixed labels, one forbidden label
pair produces a clause of up to four literals. `simplify_cnf()` runs after all
categories are concatenated (`src/models/sat_encoding.py:331-333`); the
backend is initialized only later by the solver path.

## Canonical profiling path

The read-only profiler uses the same `graph_constraints()`, `OrderVars`,
`forbid_close_labels()`, `build_cnf()`, and `simplify_cnf()` functions. It
selects the `sat_incremental_external_u` label because Phase 3B.1 showed all
three fixed-U labels have identical fingerprints. The labels are not treated
as separate encoders: all call the same construction function with externally
supplied `U`; no assumptions or solver are used.
