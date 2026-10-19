# Complete optimality certification of the fixed v2 cohort

The October 18 follow-up closes the 16 intervals left open by the earlier postprocessing. All 117 graph/parameter instances now have a validated labeling attaining an independently checked lower bound. Ten retained upper bounds improve. This is a post-hoc proof study on the original instances, not a new timed SAT–ILP comparison or a theorem for an infinite graph family.

## Weighted capacity lower bound

Let \(H=G^2\), and assign nonnegative integer weights \(w_v\), not all zero, to its vertices. Define

\[
W=\sum_{v\in V}w_v,\qquad
C=\max\left\{\sum_{v\in I}w_v:I\text{ is independent in }H\right\}.
\]

For \(h\ge k\ge1\),

\[
\boxed{\lambda_{h,k}(G)\ge k\left(\left\lceil W/C\right\rceil-1\right).}
\]

**Proof.** Normalize any feasible labeling to minimum zero and partition its labels into blocks \(\{jk,\ldots,jk+k-1\}\). Vertices in a block form an independent set in \(G^2\): their labels differ by less than \(k\), whereas every distance-one or distance-two pair requires separation at least \(k\). Each block therefore has weight at most \(C\). A span \(s\) uses at most \(\lfloor s/k\rfloor+1\) blocks, giving \(W\le C(\lfloor s/k\rfloor+1)\) and the bound. This is a rounded fractional-coloring dual bound, a classical technique, not a newly discovered general theorem.

Floating-point linear programming proposes the weights only. The certificate checker enumerates **all** maximal independent sets of the full graph square with integer arithmetic and recomputes their maximum weight. Nonnegative weights ensure that a maximum-weight independent set extends to a maximal one. The six difficult squares have 170–390 maximal independent sets, so this verification is small here; enumeration is exponential in general. No numerical LP objective, tolerance, or optimizer status is trusted.

## Constructive upper bounds and parameter transfer

Partition vertices into independent classes of \(G^2\). For \(0<k\le h\le2k\), order the classes and use gap \(h\) if successive classes contain an edge of \(G\), and gap \(k\) otherwise. Every nonconsecutive pair of classes is separated by at least \(2k\ge h\). This proves validity; it does not prove that the chosen partition is optimal. Classes may contain more than two vertices, overcoming the restriction in the earlier matching construction.

If a verified labeling has separations \((a,b)\), multiplying its labels by a positive integer \(t\) yields a valid \(L(h,k)\)-labeling whenever \(ta\ge h\) and \(tb\ge k\). In particular, doubling an \(L(2,1)\) witness yields an \(L(3,2)\) witness. A transferred labeling remains only an upper bound until it meets an independently established lower bound. Together with the capacity certificates and an additional SAT witness, these constructions close 14 of the 16 open intervals.

## Exact color, rank and residual encoding

The remaining two intervals belong to `ER_40_p0.15_seed0`. They require proving infeasibility below the incumbent, not further improving the incumbent.

At proposed span \(s\), let \(q=\lfloor s/k\rfloor+1\). Represent a label by

\[
f(v)=k\,\pi(c(v))+r_v,
\quad c(v)\in\{0,\ldots,q-1\},\quad
\pi\in S_q,\quad 0\le r_v<k.
\]

Here \(c\) is a proper coloring of \(G^2\); its colors are internal names. The permutation \(\pi\) gives their numerical ranks. For every feasible labeling, its quotient and remainder on division by \(k\) provide such a representation; unused bins are allowed. Conversely, imposing the original separations and the upper domain boundary makes every decoded representation a feasible labeling.

One-hot variables encode vertex colors and the color-to-rank permutation. Sequential at-most-one constraints implement uniqueness. A square clique can be assigned distinct **internal color names** without loss of generality, since the rank permutation remains free. Assigning its vertices fixed numerical labels would not be justified. The implementation contains two exact specializations:

- For \((h,k)=(2,1)\), residuals vanish. A Boolean flag records that two classes contain an original edge, forbidding these classes from occupying consecutive ranks. Nonconsecutive ranks already differ by at least two.
- For \((h,k)=(3,2)\), each vertex retains its own residual bit. Across consecutive ranks, an original edge requires residuals \((0,1)\) in increasing-rank order. A distance-two pair forbids residuals \((1,0)\). Rank differences of at least two give label differences at least three. At even span, the last rank permits residual zero only.

Thus the formulas are satisfiable **if and only if** a labeling within the requested span exists. Omitting residual bits or fixing numerical labels would break this equivalence. Exhaustive checks compare feasibility and decoded solutions against independent shortest-path/label enumeration on every graph with at most four vertices, over both parameter pairs and spans 0–7. Only one reflection convention is used at a time.

The new encoding is experimental. It has not replaced the original benchmark solver or undergone a controlled runtime ablation. A separate orientation-selector order encoding is also supplied and tested; its exploratory timeouts are retained, and reduced clause counts are not presented as evidence of a universal speedup.

## Lower-bound certificates from UNSAT

For `ER_40_p0.15_seed0`, the new formulas are UNSAT at span 13 for \(L(2,1)\) and at span 27 for \(L(3,2)\). Verified witnesses at spans 14 and 28 establish the respective optima. Glucose produces clausal proofs. DRAT-trim checks them and converts their RUP derivations to LRAT with explicit propagation hints. A separate standard-library checker reconstructs each CNF from the archived graph and verifies every LRAT addition through its indicated unit-propagation chain, requiring a derived empty clause.

Nine additional old solver-dependent closures receive UNSAT proofs using the original order formulation. Two other old solver-dependent closures are covered by the new capacity bound. The final disjoint classification is **91 theory/clique, 15 capacity, and 11 UNSAT certificates**, totaling **117**. These checker implementations are tested and independent of the solver, but have not themselves been formally verified in a proof assistant.

## Evidence, replay and limits

The complete package is in `results/analysis/proof_closure/v1_20261018/`. From the repository root:

```bash
.venv-1/bin/python -S scripts/verify_proof_closure.py
```

This command checks fingerprints, all labelings, exact weighted capacities, reconstructed CNFs, all 11 LRAT proofs and every reported table. It uses no NetworkX, PySAT, NumPy, Gurobi or network access. The `-S` option demonstrates that installed third-party Python packages are not used. The original 702 observations and all previous result archives are unchanged.

Complete certification settles the optima of this **finite cohort**. It does not establish an unrestricted polynomial-time algorithm, a universal formula, new worst-case complexity, or superior SAT runtime. The next useful evaluation is a separately frozen ablation of the new encoding and bounds on unseen instances, using common budgets and retaining failures. No further experiments are needed merely to establish the 117 optima reported here.

## References

- [Fractional chromatic number, G. Simonyi's course notes](https://renyi.hu/~simonyi/teaching/fractchi.pdf): primal/dual formulation.
- [Sinz, Towards an Optimal CNF Encoding of Boolean Cardinality Constraints (2005)](https://www.carstensinz.de/papers/CP-2005.pdf): sequential cardinality encoding.
- [DRUP and RUP verification](https://www.cs.utexas.edu/~marijn/drup/).
- [Cruz-Filipe et al., Efficient Certified RAT Verification](https://www.cs.cmu.edu/~mheule/publications/lrat.pdf): LRAT propagation hints and certified-checker literature. The checker in this repository is a separate implementation, not one of that paper's formally verified checkers.
