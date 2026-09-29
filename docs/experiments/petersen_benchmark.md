# Petersen benchmark scope

The constructor creates GP(n,k) with edges u_i–u_(i+1), u_i–v_i, and v_i–v_(i+k), indices modulo n, and 1 ≤ k < n/2. The default n=7..50 sweep contains 594 configurations.
GP(n,k) has **2n vertices**. Its k is the inner-ring step, not the k in L(h,k). GP_7_1 has 14 vertices; the old CSV column `n` records 14. This is an L(2,1) sweep, not a labeling-threshold sweep. See the [historical CSV guide](../../results/archive/legacy/README.md).

`results/archive/legacy/sat_petersen.csv` records 594 OPT rows: 133 with span 5, 458 with span 6, and three with span 7 (GP(10,2), GP(11,2), GP(11,5)). These data are preserved and have not been rerun with the revised solver.

Huang et al. (2012) use GPG(n), consisting of two n-cycles joined by an arbitrary matching. Sweeping k does not enumerate those matchings. When gcd(n,k)>1, the natural GP(n,k) inner ring splits into multiple cycles. Do not describe the present sweep as verification of the full Georges–Mauro conjecture.

An incumbent greater than 7 is not a counterexample: a proved lower bound greater than 7 and membership in the correct graph class are required. The revised runner distinguishes these cases and does not flag a counterexample solely from a feasible labeling.

Run `python -m benchmarks.benchmark_petersen --first 7 --last 50`. The default output is a fresh file under `results/runs/`, with metadata and witnesses.
