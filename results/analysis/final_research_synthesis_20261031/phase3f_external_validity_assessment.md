# Phase 3F external-validity assessment

The corrected final run used eight original graphs: two Trees, two Barabási–Albert, two ER p=0.15 and two ER p=0.30, with one 20- and one 40-vertex graph per family. It used `(h,k)=(3,2)`, fixed validated U values, Reference versus Threshold, fresh sequential workers and three operational repetitions.

There were 48 scheduled runs: 42 SAT with independently valid witnesses, six parent timeouts, zero UNSAT and zero worker errors. All six timeouts occurred on `ER_40_p0.30_seed100` at U=60, for both encodings and all three repetitions. They are right-censored and their counters are null; they are not UNSAT.

Formula preflight passed for 16 graph/encoding rows. Threshold reduced clauses and literals for every selected graph, with 39.0–43.0% clause and 54.9–58.0% literal reductions, while using more variables. On completed graphs, construction/loading and recorded memory generally favored Threshold. Solve-time direction varied by graph; the dense timed-out graph provides no completed comparison.

Because the cohort has only eight graphs, one parameter pair, three deterministic operational repetitions and one concentrated censored graph, Decision D—insufficient evidence for a broad external-validity claim—is appropriate. The experiment supports a restricted descriptive formula-size result, not a general practical-speed conclusion.
