# Post-Phase-3E Audit Closure and Performance Interpretation

## Scope and safeguards

This documentation-only closure read the Decision B audit outputs and the canonical Phase 3E `_02` artifacts. It did not modify prior reports, raw results, failed attempts, or historical benchmarks. No SAT, GA, ILP, benchmark, or solver backend execution occurred.

## Part A — audit closure

The closure addresses every minor gap recorded by the audit: incomplete older Phase 3A command/source provenance; unpinned environment/source revision details for Phases 3B–3D; working-tree provenance for Phase 3E; RSS-unit interpretation; and the unclassified U=111 boundary. Remediation is documentation-only and is recorded row-by-row in `audit_gap_remediation.csv`. Outstanding limitations are explicitly retained; no missing facts were invented. See `audit_gap_addendum.md`.

## Part B — authoritative Phase 3E interpretation

The final `_02` dataset contains 12 SAT runs, 6 matched block comparisons, 4 summary groups, and 12 valid witnesses. The original failed attempt and `_01` remain separate provenance and are excluded.

- **U=112:** threshold has fewer clauses and lower recorded RSS, but matched solve ratios are 0.84266594, 1.1410537, 1.12416906. It is faster in one block and slower in two. Its median end-to-end time is 38.7360094 versus 36.2671907, but this is sensitive to launch variation and is not a consistent speed claim.
- **U=127:** threshold is slower in the solve slice in all three blocks but faster end-to-end in all three because construction/loading dominates this easy case. Both encodings report zero search counters.
- **Counters:** at U=112 threshold reports more conflicts, decisions, and propagations; at U=127 both are zero. Fewer clauses do not imply better solver search.
- **Conclusion:** the strongest supported advantage is formula size and recorded memory, with span-dependent pipeline behavior and inconclusive practical solve performance.

Detailed values are in `phase3e_metric_analysis.csv` and `phase3e_interpretation.md`.

## Part C — next experiment decision

**Decision B:** investigate propagation and solver behavior on the existing ER-60 instance before extending to more graphs. A broader Phase 3F is justified only as a controlled diagnostic follow-up, not as a claim of threshold superiority. The proposed scope is recorded in `next_experiment_decision.json`; no experiment was executed here.

## Remaining limitations

Only three operational repetitions exist per encoding/span, so no strong statistical inference is appropriate. The experiment covers one graph, two spans, and fixed feasibility rather than optimization. RSS is host-specific, and U=111 remains unclassified.

## Validation

The closure manifest stores SHA-256 hashes for all authoritative `_02` inputs. The canonical result files remained unchanged during closure generation, and the historical artifacts remain untouched.
