# Phase 3C — Distance-2 Clause Generation Forensics

## Executive summary

This read-only audit used the exact ten-task Phase 3B.1 cohort and its validated
fixed spans. It built 20 canonical CNF models (tight and loose span per task),
without SAT search, GA, ILP, backend initialization, or benchmark execution.

The implementation identifies distance-2 constraints using a cutoff-2
all-pairs shortest-path map and an unordered node-pair loop. A pair with several
common neighbors is processed once, not once per two-edge path. Across all ten
tasks, the actual processing count was exactly the unique graph-theoretic count:
4,660 events and 4,660 unique pairs.

Exact clause analysis found:

- zero duplicate distance-2 clauses within a pair;
- zero duplicate distance-2 clauses across pairs;
- zero distance-2 tautologies;
- zero distance-2 clauses identical to label-domain, distance-1, or symmetry
  clauses;
- zero tautologies in the complete raw formulas.

Therefore, the large distance-2 contribution is structural, not an artifact of
duplicate or tautological emission.

## Source execution path

The detailed map is in [distance2_execution_map.md](./distance2_execution_map.md).
The authoritative path is:

`solve_graph -> graph_constraints -> _search/_search_incremental ->
_solve_span/build_cnf -> forbid_close_labels`.

`graph_constraints()` uses `nx.all_pairs_shortest_path_length(..., cutoff=2)`,
then compares unordered node pairs. It does not enumerate common neighbors.
`build_cnf()` loops once over the resulting distance-2 list. For each pair,
`forbid_close_labels()` enumerates forbidden label pairs with difference below
`k`, and `not_equal_literals()` translates each endpoint inequality into
order-encoding literals. Simplification occurs only after all category clauses
are concatenated.

The three Phase 3B.1 path labels reach the same `build_cnf()` implementation
under fixed externally supplied `U`; the canonical detailed profile uses that
same implementation and does not invoke solver assumptions.

## Pair-level inventory

The full table is in [distance2_pair_inventory.csv](./distance2_pair_inventory.csv).

| Family/task | Distance-2 pairs | Pairs with multiple common neighbors | Pairs at distance >2 |
|---|---:|---:|---:|
| ER-20 | 111 | 75 | 18 |
| ER-40 | 538 | 468 | 17 |
| ER-60 `(2,1)` | 1,253 | 1,205 | 5 |
| ER-60 `(3,2)` | 1,253 | 1,205 | 5 |
| K10,10 | 90 | 90 | 0 |
| K20,20 | 380 | 380 | 0 |
| K30,30 | 870 | 870 | 0 |
| Tree-20 | 22 | 0 | 149 |
| Tree-40 | 58 | 0 | 683 |
| Tree-60 | 85 | 0 | 1,626 |

Trees have exactly one common neighbor for every distance-2 pair. Complete
bipartite graphs have many common neighbors, but still produce one pair event
per unordered pair. The ER tasks have high multiplicity, especially ER-60,
without duplicate pair processing.

## Clause-level findings

The detailed profile is in [distance2_clause_profile.csv](./distance2_clause_profile.csv);
per-pair records are in [distance2_pair_clause_details.csv](./distance2_pair_clause_details.csv).
At ER-60 `(3,2)`, `U=127`:

| Metric | Value |
|---|---:|
| Distance-2 pairs | 1,253 |
| Distance-2 clauses | 478,646 |
| Unique distance-2 clauses | 478,646 |
| Duplicate clauses | 0 |
| Tautological distance-2 clauses | 0 |
| Identical clauses in other categories | 0 |
| Clauses per distance-2 pair | 382 |

The clause count agrees exactly with the existing category counter and with the
independent pair-by-pair sum. For the free-endpoint encoding, the number of
clauses per pair is the number of ordered label pairs `(a,b)` in `0..U` with
`|a-b| < k`; for `k=2`, this is `4U-2`, giving `382` at `U=127`.
This is a derivation of the current emission loop, not an alternative encoding.

The largest profiled distance-2 share is ER-60 `(3,2)`, `U=127`: 59.0% of the
raw formula. Across family aggregates, ER `p=0.30` averaged 45.8%, bipartite
stress 23.5%, and trees 28.4% over the profiled tight/loose models.

## Cost observations

Distance-2 clause generation is structurally expensive because it scales with:

1. the number of unique distance-2 pairs;
2. the number of forbidden label pairs, which grows quadratically with `U` for
   fixed positive `k`;
3. Python list/literal allocation for every emitted clause.

The project simplifier was also measured separately. In the profiled models,
raw and simplified clause counts were equal, and no tautologies or exact
duplicates were removed. Simplification can therefore be a measurable cost
without reducing this cohort's formula size; it should be optimized or changed
only in a separate correctness-controlled experiment.

## Mathematical correctness discussion

- **Proven:** the current pair enumeration is unique for the given simple
  undirected graph and node order because it tests each unordered node pair once.
- **Observed:** no duplicate or tautological clauses occurred in 20 models.
  This is evidence for this cohort, not a universal theorem for all fixed-label
  or symmetry configurations.
- **Not proven:** multiple common neighbors imply no removable constraint.
  The current encoder constrains the endpoint pair, and shared paths do not
  make that constraint logically redundant by themselves.
- **Not proven:** fewer clauses would improve SAT runtime. Formula size and
  solving performance must be measured independently.

No SAT solving was used to infer redundancy or equivalence.

## Recommendation and decision gate

The strongest supported candidate is a separate, controlled investigation of an
equivalent distance-2 encoding, because distance-2 clauses dominate the target
formula and accidental duplicates cannot be removed. A secondary, lower-risk
investigation could measure pair-discovery overhead or local clause-template
caching, but neither reduces the CNF itself.

**Decision: A — a concrete, mathematically justified candidate exists and should
proceed to a separate controlled optimization experiment.** The candidate is
not yet an implementation: any replacement must provide a proof or independent
equivalence validation, preserve decoding, and report SAT/UNSAT/UNKNOWN behavior.

## Limitations

1. The ten-task cohort is not a full benchmark and timing results are descriptive.
2. Exact duplicate analysis retained one model's canonical distance-2 clause
   tuples at a time; it did not attempt general clause subsumption.
3. The current cohort has no active symmetry clauses or fixed-label distance-2
   branches, so those branches were source-traced but not empirically profiled.
4. No backend preprocessing, learned clauses, or SAT search costs were measured.

## Audit status

**PASS — source path, pair uniqueness, clause uniqueness, tautology status, and
fixed-span profiles were reconciled without changing historical data.**
