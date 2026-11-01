# Phase 3E Interpretation and Audit Closure

## Scope

This addendum uses only the canonical final dataset in
`results/runs/phase3e_threshold_sat_performance_20261031_02/`. It does not
combine the original failed attempt or `_01`, and it does not rerun any
solver. There are three operational repetitions per encoding/span. They are
controlled repeated launches, not independent stochastic samples.

## Audit closure

The audit's Decision B findings are documented in `audit_gap_remediation.csv`.
The remediations are documentation-only: no missing historical source
revision, dependency lock, or U=111 proof has been fabricated. The exact
remaining limitations are preserved in that table. The RSS interpretation is
now explicit: values are the existing macOS `ru_maxrss / 1024` readings,
retained without relabeling or cross-platform inference.

## U=112

Reference and threshold use identical solver configuration and fixed graph
inputs. Per-run metrics are in `phase3e_metric_analysis.csv` and the source
CSV. Summary `(min, median, max, range)` values are:

| Metric | Reference | Threshold | Candidate/reference median |
|---|---:|---:|---:|
| encoding construction | 1.64986142 (1.5265713-3.52958164, range 2.00301034) | 0.77945223 (0.757364493-0.828509999, range 0.071145506) | 0.472434969 |
| solver initialization | 0.000166483998 (0.000161751999-0.002276892, range 0.00211514) | 0.000136545998 (0.000122212998-0.000170428, range 4.82150026e-05) | 0.820174905 |
| clause loading | 0.741877307 (0.59748307-1.33707211, range 0.73958904) | 0.341052896 (0.321418182-0.36928311, range 0.047864928) | 0.459716038 |
| solve | 33.8752855 (33.3918457-44.3148251, range 10.9229794) | 37.5380797 (37.3425937-38.6535198, range 1.31092606) | 1.10812586 |
| pipeline | 34.6173293 (33.9894905-45.6541741, range 11.6646836) | 37.9074994 (37.6641823-38.9946949, range 1.33051256) | 1.09504402 |
| end-to-end | 36.2671907 (35.5160618-49.1837557, range 13.6676939) | 38.7360094 (38.4215468-39.7741471, range 1.35260029) | 1.06807306 |
| recorded peak RSS | 462484 (455672-495376, range 39704) | 271728 (267532-277020, range 9488) | 0.587540326 |
| conflicts | 153033 (153033-153033, range 0) | 189756 (189756-189756, range 0) | 1.23996785 |
| decisions | 602897 (602897-602897, range 0) | 649116 (649116-649116, range 0) | 1.07666152 |
| propagations | 39904336 (39904336-39904336, range 0) | 62276675 (62276675-62276675, range 0) | 1.56064932 |
| restarts | 5056 (5056-5056, range 0) | 4941 (4941-4941, range 0) | 0.977254747 |


The matched solve ratios across blocks 1-3 are 0.84266594, 1.1410537, 1.12416906. The corresponding end-to-end ratios are 0.781183671, 1.09669777, 1.09066173. Thus threshold is faster in block 1 but slower in blocks 2 and 3. It has a lower recorded RSS in all three pairs, but higher conflicts, decisions, and propagations in every pair. This is a mixed solver result, not a consistent speed advantage.

## U=127

At U=127, both encodings are easy for CaDiCaL195 and all solver counters are
zero. Summary `(min, median, max, range)` values are:

| Metric | Reference | Threshold | Candidate/reference median |
|---|---:|---:|---:|
| encoding construction | 1.79363769 (1.78825246-2.13059012, range 0.342337667) | 0.84968117 (0.846143166-0.864769701, range 0.018626535) | 0.473719512 |
| solver initialization | 0.000118693002 (0.000118421001-0.000134033002, range 1.56120004e-05) | 0.000118232001 (0.000116375999-0.000119049, range 2.67300129e-06) | 0.996116022 |
| clause loading | 0.675009653 (0.643633901-0.714814648, range 0.071180747) | 0.358924361 (0.357857485-0.361289939, range 0.003432454) | 0.53173219 |
| solve | 0.011144165 (0.008684626-0.011990954, range 0.003306328) | 0.019615857 (0.019183873-0.021351652, range 0.002167779) | 1.76019083 |
| pipeline | 0.6838127 (0.655758888-0.726077506, range 0.070318618) | 0.380394245 (0.377160407-0.381022172, range 0.003861765) | 0.556284265 |
| end-to-end | 2.47206516 (2.44939657-2.85666763, range 0.407271054) | 1.23070334 (1.22653741-1.24193011, range 0.015392697) | 0.497844217 |
| recorded peak RSS | 285272 (284380-286032, range 1652) | 153296 (152884-153436, range 552) | 0.537367845 |
| conflicts | 0 (0-0, range 0) | 0 (0-0, range 0) |  |
| decisions | 0 (0-0, range 0) | 0 (0-0, range 0) |  |
| propagations | 0 (0-0, range 0) | 0 (0-0, range 0) |  |
| restarts | 0 (0-0, range 0) | 0 (0-0, range 0) |  |


The matched solve ratios are 1.76019083, 2.45855746, 1.59986211; end-to-end ratios are 0.430817828, 0.496159014, 0.507035129. Threshold is faster end-to-end in all three blocks, mainly because its encoding/loading pipeline is shorter; it is slower in the solve slice in all three blocks. With zero conflicts, decisions, propagations, and restarts for both encodings, solver-statistic superiority cannot be inferred.

## Interpretation

The threshold encoding has a clear formula-size and recorded-memory advantage:
it has fewer clauses (405,550 vs 715,129 at U=112; 459,400 vs 810,814 at
U=127) and lower recorded RSS in every run. It does not have a consistent
solve-time advantage. At U=112, the threshold encoding has lower median
end-to-end time only if the unusually slow first reference launch is included
in an unpaired median; matched blocks show one win and two losses. At U=127,
it wins end-to-end while losing the solve slice, demonstrating span-dependent
behavior and the importance of separating construction/loading from search.

Fewer clauses do not by themselves establish better propagation. At U=112,
the threshold model reports more conflicts, decisions, and propagations than
the reference model despite fewer clauses. At U=127 all these counters are
zero. The data therefore support a memory/formula-size advantage and
span-dependent pipeline behavior, but the practical solver-performance
conclusion is inconclusive on this single graph and three repeated launches.
No optimality claim is made; U=111 remains unclassified.
