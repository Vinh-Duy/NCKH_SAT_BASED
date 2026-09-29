# General L(h,k): formulations and research scope

## Shared conventions

`solve_graph(..., h=2, k=1)` in both SAT and ILP uses integer labels starting at 0. Edges require differences at least h; only pairs at distance **exactly 2** require differences at least k. The optimal span is max−min; translating the minimum to 0 preserves all constraints. The maximum label of an unnormalized solution is a feasible upper bound, not automatically the optimal span. The API accepts nonnegative integer h,k, rejecting bool, float, and string values. The main research domain is h≥k≥1.

SAT uses `x[v,a] <=> f(v)<=a`, with constants x[v,-1]=false and x[v,s]=true. A forbidden label pair produces `¬x[u,a] ∨ x[u,a-1] ∨ ¬x[v,b] ∨ x[v,b-1]`. This clause **excludes** a violating pair; it is not an implication from an already-assumed separation condition. Boundaries and fixed vertices are replaced by constants.

Assignment introduces variables for every label in 0..U and forbids all pairs with |a−b|<h or <k. For d>0 and t=min(U,d−1), the forbidden-pair count is F(U,d)=(U+1)(2t+1)−t(t+1); F(U,0)=0. The constraint count is 2|V|+|E|F(U,h)+|D2|F(U,k). Big-M uses M=U+max(h,k), sufficient to deactivate the unselected branch on 0..U. U comes from a greedy labeling valid for h,k, not a reused L(2,1) upper bound.

## Lower bounds and search correctness

Let Δ be maximum degree and m=min(h,k). If an edge exists, L=h+(Δ−1)m is a valid lower bound for any simple graph. In the closed neighborhood of a degree-Δ vertex, all pairs have distance ≤2, so labels are separated by at least m. Sort the Δ+1 labels: all Δ successive gaps are at least m, and at least one gap next to the center's label is at least h. Their sum is at least h+(Δ−1)m. The proof also holds for h<k and zero thresholds. Edgeless graphs use L=0.

Greedy excludes a width-2h−1 label interval around each labeled neighbor and width-2k−1 around each labeled distance-2 vertex; a zero threshold forbids no labels. SAT maintains [L,U], raising L only after UNSAT. Timeout retains a feasible incumbent and returns FEASIBLE unless optimality has been established. Both worker and validator receive h,k.

Symmetry policy is not extended arbitrarily: only C_n automatically fixes f(0)=0. Cartesian families with valid metadata use only proved reflection orders. Random trees do not use root fixing. If h or k is 0, strict orders are disabled because compared vertices may share a label.

## Interpreting tree_L_hk.pdf and supervisor guidance

The supplied three-page document is an orientation survey. A reasonable experimental use is to start with paths/stars as references, then examine structured and random trees. A table saying “no formula found” does not prove that a problem is open or that a computed result is new.

At least two statements require restricted interpretation:

- The path table says “all h,k,” but for n=3, h=1,k=3, labels (0,1,3) have span 3. The endpoints require separation at least 3, so the optimum is 3, not h+k=4. Benchmarks apply path formulas only for h≥k≥1.
- NP-hardness on all trees does not imply NP-hardness on every subclass, such as paths or stars. Jan Kratochvíl's [research page](https://kam.mff.cuni.cz/~honza/research1.htm) records tree NP-completeness for q>1 coprime to p. This supports studying (3,2), but does not exclude polynomial algorithms for every listed subclass. The September 27 review checked the original Fiala–Golovach–Kratochvíl ICALP 2008 publisher abstract, which explicitly states NP-hardness when q does not divide p. See the [literature review](../literature_review.md); the duplicate FPT PDF is not the original tree-complexity paper.

Current reference formulas for h≥k≥1:

| Family | Reference value |
|---|---|
| P1 | 0 |
| P2 | h |
| P3, P4 | h+k |
| Pn, n≥5 | min(h+2k,2h) |
| K1,Δ, Δ≥1 | h+(Δ−1)k |
| Nonempty trees with h=k | hΔ |

The star lower bound follows from its closed neighborhood and is attained by center 0 and leaves h,h+k,...,h+(Δ−1)k. For h=k, color the tree square with Δ+1 colors and multiply color values by h; a closed neighborhood gives lower bound hΔ. Path formulas were checked on small instances and are not used as solver bounds, avoiding circular testing against the same formula.

## Benchmarks and reproduction

`benchmark_lhk_general.py` defaults to CxC, CxP, PxP with n,m=3..4 and pairs (1,1),(2,1),(3,2): 36 instances. `--pairs` accepts other pairs. Each run selects one backend/configuration so methods are not mixed in summaries. `--symmetry` is off by default and applies only to SAT. Older runners remain L(2,1).

`--family trees` is an initial exploration with four families:

- path: n vertices;
- star: n leaves, n+1 vertices;
- comb: Pn with one new leaf per vertex, 2n vertices;
- random: an n-vertex random labeled tree using `nx.random_labeled_tree` with an explicit seed.

This does not cover all 11 rows of the supplied survey table. General caterpillars, lobsters, brooms, spiders, double stars, and complete branching trees need separate parameter-domain designs. Combs are only a special case of caterpillars. Random trees represent neither all trees nor worst cases.

CSV records h,k, vertex/edge counts, Δ, status, runtime, and bounds; witnesses include graphs and labels. IDs contain graph names and h,k so resume does not skip different parameter pairs. Manifests contain configurations, environment versions, and source hashes. FEASIBLE is excluded from optimal-solution statistics. Baseline_Check=UNPROVEN when not OPT, even if the incumbent equals the reference; the reference does not alter solver status. SAT time includes preprocessing and worker management. ILP time includes construction and solving, while native TimeLimit applies only to optimize. These mechanisms are not identical hard deadlines.

main_r1 data and generated tables/figures remain historical L(2,1) results; measurements and metadata are unchanged. Source-hash changes after extension are expected; do not resume historical runs using new code. The historical exporter requires matching manifests, so use `make pdf` to compile saved tables. Do not supply general-parameter CSVs to the main_r1 exporter, which uses a symmetry-specific schema.

## Automated validation

`tests/test_lhk_general.py` uses an independent exhaustive oracle on all nonisomorphic graphs with at most four vertices, comparing Glucose/CaDiCaL and linear/hybrid search. Parameter pairs include the three research pairs, h<k, h=0, and k=0. Tests check greedy feasibility and lower-bound safety. Gurobi and CPLEX assignment builders are evaluated on every label tuple of small graphs; Big-M is checked over all binary directions. Tests also cover worker timeout, noninteger vertex names, tree references, and Cartesian symmetry on/off.

Builder arithmetic checks do not replace optimizer integration tests. Commercial integration tests run only with an available runtime/license; skipped tests must not be described as experimental validation of general Gurobi/CPLEX behavior.

## Historical checks from the initial extension

These test counts are an implementation-time snapshot, not the current total. See the [CSV catalog](../results_catalog.md) and [data dictionary](../data_dictionary.md) for smoke interpretation; functional checks are not main performance benchmarks.

- `python -m unittest discover -s tests -q`: 36 tests, 34 passed, two commercial integration tests skipped because Gurobi/CPLEX were unavailable.
- `results/archive/pilots/lhk_cartesian_smoke.csv`: n=m=3, three families × three pairs = nine instances, all OPT. Each witness was reread and independently checked against its CSV row.
- `results/archive/pilots/lhk_trees_smoke.csv`: n=3..5, seeds 0 and 1, 45 instances, all OPT; 27 had applicable references and all passed, 18 had no applicable reference.
- Resuming the Cartesian smoke left its CSV unchanged without duplicate witnesses.
- These are functionality checks, not broad performance evidence. Their runtimes must not be compared because the runs executed concurrently.
- `make pdf` compiled the manuscript with the saved L(2,1) tables.
