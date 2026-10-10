# Consolidated evidence summary

The [reviewed report](0700e674e1e6ba4e/README.md) supplies manuscript Table 9.
It brings the baseline and clique-augmented classifications of the same
117 instances into one table, grouped by graph family and (h,k).

| Cases | Theory before clique | Other closed before clique | Open before clique | Clique-certified | Closed after | Open after |
|---:|---:|---:|---:|---:|---:|---:|
| 117 | 61 | 35 | 21 | 50 | 98 | 19 |

The 50 clique-certified optima overlap the original closed cases: **only two
are newly closed**. Thus 61 + 35 + 2 = 98, and 98 + 19 = 117. The clique
column is not an additional disjoint category.

Both the before and after columns use the completed **v2** run; archived v1
categories are checked separately and happen to match the v2 baseline on all
117 instances. V1 intervals and runtimes are not combined with v2 data.
Per-run statuses, times, and optimality coverage are unchanged.

- [Summary CSV](0700e674e1e6ba4e/summary.csv): 15 family/parameter rows plus one total.
- [Instance CSV](0700e674e1e6ba4e/instances.csv): 117 rows with v1/v2 categories and bounds.
- [LaTeX table](0700e674e1e6ba4e/summary.tex).
- [Source fingerprints](0700e674e1e6ba4e/sources.json).

`make evidence-data` revalidates and exports this summary without running either
solver. `make pdf` compiles the selected table. The final total is a combination
of available evidence, not the number solved by either backend within 30 seconds.
