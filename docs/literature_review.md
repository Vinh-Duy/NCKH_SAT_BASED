# Literature review and manuscript scope

Review dated September 27, 2026. The topic remains **SAT-Based Approach for L(h,k)-Labeling of General Graphs**. The main problem is **vertex** labeling with shortest-path distance-1 and distance-2 constraints. The four additional PDFs inform related work; their variants do not automatically expand implementation scope.

**September 27 evening addition:** `outline_L(hk).pdf` and `genetic.pdf` were read. The outline is a working document, not evidence of novelty. Murugan (2015) on coronas and Sarhan et al. (2026) on radio-labeling GA were added to the bibliography; GA has not been implemented or evaluated.

## Identifying the references

| Supplied filename | Actual work / cited version | Use |
|---|---|---|
| `newSURVEY.pdf` | Calamoneri, L(h,k) survey, The Computer Journal 54(8), 1344–1371 (2011) | Foundations and pointers to original papers; the same survey supplied earlier |
| `fixed para.pdf` | Fiala, Gavenčiak, Knop, Koutecký, Kratochvíl; arXiv:1507.00640v2 (2015) | Structural parameters, not a separate tree-only paper |
| `complexity L(h,k) on tree.pdf` | **Byte-identical to `fixed para.pdf`** | Count once; do not duplicate the citation |
| `L(pq) edge.pdf` | Berthe, Martin, Paulusma, Smith; supplied arXiv v4 (2022), published in Algorithmica 85, 3406–3429 (2023) | Edge/line-graph labeling; distinguish distance conventions |
| `The_L_h_1_1_labelling_problem_for_trees_2009.pdf` | King, Ras, Zhou, European Journal of Combinatorics 31(5), 1295–1306 (**2010**) | Distance-3 extension; online publication in 2009 does not replace the volume year |

The duplicate PDFs share SHA-256 `196b22890c6f61009029c762bafd2ad6f60acd5dbf9502a9270015800c3b059a`. Full reference texts are not copied into the repository.

The FPT paper has a journal version titled **Parameterized complexity of distance labeling and uniform channel assignment problems**, Discrete Applied Mathematics 248, 46–55 (2018). The author's [publication list](https://kam.mff.cuni.cz/~fiala/papers/publications.pdf) identifies its relation to COCOON 2016. `10.4230/LIPIcs.xxx.yyy.p` in the supplied PDF is a placeholder, **not a valid DOI**. The manuscript uses checked publication metadata and DOIs, not filenames as titles.

Bibliography DOIs:

- Survey: [10.1093/comjnl/bxr037](https://doi.org/10.1093/comjnl/bxr037).
- FPT: [10.1016/j.dam.2017.02.010](https://doi.org/10.1016/j.dam.2017.02.010).
- Edge labeling: [10.1007/s00453-023-01120-4](https://link.springer.com/article/10.1007/s00453-023-01120-4).
- L(h,1,1): [10.1016/j.ejc.2009.11.006](https://doi.org/10.1016/j.ejc.2009.11.006).

## Implications for the research

**Tree complexity.** The filename `complexity...tree.pdf` is not the title of the original complexity paper. The survey and FPT paper cite Fiala–Golovach–Kratochvíl (ICALP 2008). The [original publisher page](https://link.springer.com/chapter/10.1007/978-3-540-70575-8_25) states NP-hardness of minimum-span labeling on trees when q does not divide p. This motivates (3,2), but does not imply that every random tree is difficult or every subclass lacks a formula. Fast solutions on the 50 sampled trees do not contradict the theorem.

**FPT.** The result jointly controls structural parameters and thresholds. Fixing h,k alone does not imply polynomial-time solvability on all graphs. The pipeline does not implement this FPT algorithm. The experimental implication is to vary structure, not only vertex count.

**Edge labeling.** A line-graph connection is possible, but the paper uses “a path of length 2” while the code uses “shortest-path distance exactly 2.” They agree for h≥k and differ on triangles when h<k. No edge benchmark or validator change has been introduced.

**L(h,1,1).** This variant adds a distance-3 condition. Labels 0,2,4,0 on P4 are valid L(2,1) but not L(2,1,1). A lower bound for a more constrained problem is not automatically a lower bound for the current problem. These results are not pooled into L(h,k) CSVs.

**L(2,1).** It remains the default as a classical case with many references, not as the “strongest constraint” regime. Increasing h or k cannot enlarge the feasible set. (1,1), (2,1), and (3,2) remain suitable exploratory pairs.

## The supervisor's paper

[A SAT-Based Exact Approach for Radio k-Labeling](https://arxiv.org/abs/2607.19997) is cited as an **arXiv preprint**, reported by the supervisor as under review. No journal, volume/pages, journal DOI, or acceptance status is invented. The public paper informs structure; its results and figures are not used as this project's experimental data.

The mathematical/methodological relationship is discussed in `paper/sections/related_work.tex`. Order encoding and incremental SAT are not claimed as previously unknown ideas, and supervision does not automatically imply coauthorship. The project's authors and affiliations await confirmation.

## Applied manuscript structure and presentation

The working format is a single-column 11pt LaTeX article without a report-style table of contents:
Abstract/Keywords → Introduction → Problem → Related Work → SAT/ILP models → Search/Symmetry → Experiments → Discussion → Conclusion → References → appendices on bounds, graph families, and L(2,1) symmetry data.

The preprint and [official Springer guidance](https://link.springer.com/journal/11276/submission-guidelines) inform numbered figures/tables, in-text references, self-contained captions, explicit data sources, and readable final-size text. Method illustrations are drawn in code; plots use audited CSVs and are exported as vector PDFs and 300-dpi PNGs. This is a neutral working format, **not a claim of compliance with a Wireless Networks, IEEE, or ACM submission template** before a venue is chosen.

New figures show a P5 labeling and threshold matrix, span-search flow, and median/IQR runtime plus paired scatter for 50 trees. IQR measures variation across seeds, not a confidence interval. Pilot tables have been audited and integrated; see the [audit](../results/analysis/general_pilot_v1/README.md). Unexecuted plans, including GA, remain separate from measured results.

The September 29 language revision presents the manuscript and maintained documentation in English. A venue-specific template and required declarations should be adopted only after selecting the submission venue. The English title retains the agreed research topic.
