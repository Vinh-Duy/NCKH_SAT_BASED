# ILP formulations

The label domain is 0..U, where U comes from a greedy labeling. `assignment` uses one binary variable per vertex–label pair and one span variable. Each vertex selects exactly one label; label pairs that are too close on edges or distance-2 pairs are forbidden, and selected labels cannot exceed the span variable.

`big-m` uses integer labels, a span variable, and one direction variable per constrained pair. M=U+max(h,k) suffices to deactivate the unselected branch of the absolute-difference constraint; the default L(2,1) case gives M=U+2. U comes from a labeling valid for the requested h,k, not from an L(2,1) bound reused after changing parameters.

Both formulations use a MIP start, set the MIP gap to 0, and validate labels within the solver API. Assignment does not fix an arbitrary vertex to 0: on P4, fixing an endpoint to 0 can exclude span-3 solutions. Translation guarantees only that some vertex receives 0. Gurobi and CPLEX are optional imports.

Native time limits apply to optimization; API runtime also includes graph-constraint generation, model construction, and validation. Errors and infeasibility are not interpreted as timeouts. Commercial backend runtimes/licenses must be installed separately. `benchmark_sat_vs_ilp.py` additionally places the entire SAT/ILP worker under an external deadline; its CSV `Wall_Time` differs from API runtime.

Assignment has n(U+1)+1 variables: n(U+1) binary variables and one span variable. `Variables` does not count binary variables only. ILP constraints are not equivalent to SAT clauses. See the [data dictionary](../data_dictionary.md).

Complete formulas, size counts, and the one-based label convention are in the [LaTeX model section](../../paper/sections/models.tex).
