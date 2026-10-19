# Construction validation on new graph samples

This supplementary experiment evaluates the frozen color-order construction after its exploratory use on the original 117 instances. It measures labeling quality and mathematical certificate coverage. It does not measure SAT/ILP performance and does not add observations to the original comparison.

## Design fixed before execution

The [protocol](../../experiments/certificate_validation_v1.json) was saved before execution. The preparation step snapshots the canonical graphs, protocol, source hashes and Python/NetworkX versions. This is a locally fixed protocol, not an external preregistration.

- Random graphs: 20, 40 and 60 vertices; graph seeds 100--104; random labeled trees, BA with two attachment edges, and ER with edge probabilities 0.15 and 0.30. This gives 60 graphs.
- Structural stress cases: three grids (3 by 7, 4 by 9, 5 by 11), three cycles (20, 40, 60 vertices), and three complete bipartite graphs with parts of size 10, 20 and 30.
- Each of the 69 graphs uses parameters (1,1), (2,1), (3,2): 207 graph/parameter instances.
- Five methods give 1,035 observations. No graph is removed because it is disconnected, difficult or unsuccessful.
- Canonical labeled edge-set hashes do not overlap the original cohort. Isomorphism is not an exclusion criterion; new seeds do not assert nonisomorphism.

Graph seeds specify graph generation. Algorithm seed 0 specifies ordering choices and remains the same across instances. The 100-attempt limit is an algorithmic cap, not a time budget. Multiple parameter pairs share one graph and must not be treated as independent graph samples.

## Five methods

1. `greedy`: visit vertices in index order and assign the smallest currently valid label.
2. `matching_h`: use the existing maximum-matching pair/singleton partition of the graph square and separate consecutive classes by h. This is always feasible for h >= k.
3. `random_order`: shuffle that same partition up to 100 times, retaining an order with no original edge between consecutive classes when h > k. Successful orders use spacing k.
4. `insertion_order`: the frozen insertion heuristic in `construct_color_order.py`, with the same partition, seed and attempt cap.
5. `dsatur_h`: apply NetworkX's saturation-largest-first greedy coloring to the square, then multiply colors by h. This is a simple feasible baseline, not an exact coloring algorithm or an optimized L(h,k) heuristic.

When h=k, both ordering methods use the canonical order without search. When h>k, successful orders of the same partition all have span k(r-1), where r is its class count. Thus the ordering comparison measures success at finding a compatible order, not span improvement among successful orders. The (2,1) and (3,2) compatibility searches are identical on the same graph.

## Certificates and audit

The common lower bound is the maximum of h+(Delta-1)k for nonempty edge sets, a checked square-clique bound, and the restricted [matching bound](../methods/matching_certificates.md) when applicable. The degree bound is zero for edgeless graphs. Clique search is deterministic greedy search from each vertex; no maximum-clique claim is made. Family-specific exact formulas are deliberately outside this common pool.

`Certified=True` means a validated labeling attains this mathematical lower bound. A positive gap is only a gap to this certificate pool: it does not prove the labeling suboptimal, or imply that no exact formula exists. `UNKNOWN` means no order was found within the attempt budget and is not an infeasibility result.

The standard-library checker verifies all embedded graphs, 907 feasible labelings, 163 matching certificates, shared partitions, observation coverage, CSV fields, summaries and archive hashes. The experiment does not rely on solver-reported lower bounds. Mathematical soundness is justified separately from the finite tests.

## Results and interpretation

The [audited archive](../../results/analysis/certificate_validation/v1_20261017/README.md) contains all outcomes. Insertion order produces 191 feasible proposals, certifies 53 instances, and improves on greedy in 57 cases. Random ordering produces 95 feasible proposals and certifies 22. Removing the 69 equal-parameter controls gives 122/138 versus 26/138 successful ordering observations; these are descriptive dependent outcomes, not a significance test.

DSATUR-h certifies 58 instances, all for (1,1). Insertion certifies 22 equal-parameter and 31 unequal-parameter instances. Its strongest group is ER p=0.30, with 43/45 certificates; it certifies no tree, grid, cycle or ER p=0.15 instance in this new cohort. Pair/singleton partitions can be wasteful when the graph square admits larger independent sets. The DSATUR-h baseline is itself conservative when h>k because it spaces every color by h.

The union of the five methods certifies 96/207 instances; this is a union of evidence, not the coverage of a timed portfolio solver. The other 111 remain uncertified by the tested constructions and bounds. No exact solver was run on them. Matching certificates apply to 39 parameter instances but never strengthen the checked degree/clique bound. The original cohort remains at 101 closed and 16 open intervals, with 90 independently supported closures.

The new observations support a family-dependent construction result, not a universal heuristic advantage or a SAT speedup. They also prevent selecting only the successful dense instances when reporting the construction. They do not establish performance on larger graphs or under multiple algorithmic seeds.

## Reproduction

Verify and regenerate derived tables without rerunning construction:

```bash
make certificate-validation-data
```

Run a fresh copy of the fixed experiment in an unused directory:

```bash
.venv-1/bin/python benchmarks/benchmark_certificate_validation.py prepare --output results/analysis/certificate_validation/reproduction_1
.venv-1/bin/python benchmarks/benchmark_certificate_validation.py run --output results/analysis/certificate_validation/reproduction_1
.venv-1/bin/python -S scripts/audit_certificate_validation.py --input results/analysis/certificate_validation/reproduction_1
```

Preparation refuses an existing directory. Execution refuses changed sources, environment, graphs or protocol, and refuses a previously started output. An interrupted study retains a progress log but is not a completed report. Reproduction requires the recorded source versions and environment; comparing exact matching choices across different library versions is not guaranteed.
