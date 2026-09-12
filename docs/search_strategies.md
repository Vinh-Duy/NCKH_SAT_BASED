# Span Search Strategies

## 1. Fixed-Span Feasibility

For a graph $G$, let $L$ be a valid lower bound and $U$ a feasible greedy upper bound. For each candidate span $s$, the SAT model asks whether an $L(2,1)$-labeling exists with labels in $\{0,\ldots,s\}$.

The feasibility predicate is monotone:

$$
\mathrm{SAT}(s)=\text{true}
\implies
\mathrm{SAT}(s')=\text{true}\quad\forall s'\ge s.
$$

Therefore, the optimal span is

$$
\lambda^*=\min\{s\in[L,U]:\mathrm{SAT}(s)=\text{true}\}.
$$

The implementation starts from the degree lower bound and a greedy feasible upper bound, then uses the selected search strategy to identify $\lambda^*$.

## 2. Linear Search

The linear strategy tests candidate spans in descending order:

$$
U, U-1, U-2,\ldots,L.
$$

Each satisfiable result replaces the current best solution with a smaller span. Once a candidate $s$ is found to be UNSAT after a feasible span has already been found, the previous feasible span is optimal.

For example, if the sequence is

```text
L6:SAT -> L5:SAT -> L4:UNSAT
```

then $\lambda^*=5$. If the search reaches $L$ with SAT, the mathematical lower bound proves optimality immediately.

### Advantages

- Simple control flow and transparent proof history.
- Efficient when the greedy upper bound is close to the optimum.
- The first UNSAT result directly certifies the preceding feasible span.

### Limitations

- It may solve many consecutive spans when $U-L$ is large.
- Performance is sensitive to the quality of the initial greedy upper bound.

## 3. Hybrid Search

The hybrid strategy first performs a binary search over the monotone feasibility predicate. Let $[low,high]$ initially equal $[L,U]$. At each step, test

$$
mid=\left\lfloor\frac{low+high}{2}\right\rfloor.
$$

If $mid$ is SAT, set $high=mid$ and retain the labeling. If $mid$ is UNSAT, set $low=mid+1$. This phase narrows the interval containing the minimum feasible span in logarithmically many solver calls.

After the binary phase, the implementation explicitly solves the candidate $low$ if necessary. It then checks the immediately smaller span sequentially:

$$
low-1.
$$

An UNSAT result at $low-1$ proves that the feasible candidate $low$ is optimal. This final check is important because a binary search can identify a boundary candidate but should still record a direct infeasibility certificate for the neighboring span.

A typical history is:

```text
B8:UNSAT -> B12:SAT -> B10:SAT -> B9:UNSAT -> S9:UNSAT
```

The exact history depends on the initial bounds and solver outcomes.

### Advantages

- Reduces the number of feasibility tests when the initial interval is wide.
- Preserves a final UNSAT check for an explicit optimality certificate.
- Works naturally with the monotonicity of the span feasibility predicate.

### Limitations

- Each binary decision still requires a complete SAT call.
- A timeout during either phase may yield `FEASIBLE` rather than `OPT`.
- The quality of the returned status depends on preserving the best valid labeling found before interruption.

## 4. Timeout and Status Semantics

Each fixed-span SAT call receives the remaining time budget. The solver can return `SAT`, `UNSAT`, or `TIMEOUT`; decoded SAT models are independently validated. The benchmark status is interpreted as follows:

- `OPT`: a feasible span has been established and a smaller neighboring span is proven UNSAT, or the mathematical lower bound is reached.
- `FEASIBLE`: a valid labeling is available, but the remaining proof search was interrupted.
- `TIMEOUT`: no completed feasible labeling is available before the time limit.
- `INVALID`: a decoded solver model fails the independent labeling validator.

The search history is retained internally so that the benchmark log records the sequence of tested spans and outcomes.
