# ILP Formulations for $L(2,1)$-Labeling

## 1. Common Notation

Let $G=(V,E)$ be a graph, let $E_2$ contain the unordered vertex pairs at distance two, and let $U$ be a feasible greedy upper bound. Labels are restricted to $\{0,1,\ldots,U\}$. The span variable is denoted by $\lambda$.

Both formulations minimize the span and use a greedy labeling as a warm start when supported by the selected backend.

## 2. Big-M Formulation

The Big-M model assigns one integer label variable to each vertex:

$$
f_v\in\mathbb{Z},\qquad 0\le f_v\le U \quad \forall v\in V,
$$

and an integer span variable

$$
0\le\lambda\le U.
$$

### Objective

$$
\min\lambda.
$$

### Span Constraints

Every vertex label must not exceed the span:

$$
f_v\le\lambda \quad \forall v\in V.
$$

### Edge Constraints

For each edge $(u,v)\in E$, introduce a binary direction variable $z_{uv}$. With $M=U+2$, impose

$$
f_u-f_v\ge 2-Mz_{uv},
$$

and

$$
f_v-f_u\ge 2-M(1-z_{uv}).
$$

When $z_{uv}=0$, the first inequality enforces $f_u-f_v\ge2$; when $z_{uv}=1$, the second enforces $f_v-f_u\ge2$. Thus $|f_u-f_v|\ge2$.

### Distance-Two Constraints

For every $(u,v)\in E_2$, introduce a binary direction variable $z_{uv}^{(2)}$ and impose

$$
f_u-f_v\ge 1-Mz_{uv}^{(2)},
$$

$$
f_v-f_u\ge 1-M(1-z_{uv}^{(2)}).
$$

These constraints enforce $|f_u-f_v|\ge1$.

### Warm Start

The greedy labeling supplies initial values for $f_v$ and initializes $\lambda$ to $U$. Gurobi and CPLEX can use these values as a MIP start.

## 3. Binary Assignment Formulation

The assignment model uses binary variables

$$
x_{v,k}\in\{0,1\},
$$

where

$$
x_{v,k}=1 \iff f(v)=k.
$$

It also uses an integer span variable $\lambda$ with $0\le\lambda\le U$.

### Objective

$$
\min\lambda.
$$

### Unique Assignment

Each vertex receives exactly one label:

$$
\sum_{k=0}^{U}x_{v,k}=1 \quad \forall v\in V.
$$

### Span Bound

The selected label of every vertex must not exceed $\lambda$:

$$
\sum_{k=0}^{U}k\,x_{v,k}\le\lambda \quad \forall v\in V.
$$

### Edge Separation

For every edge $(u,v)\in E$ and every pair of labels whose difference is at most one, add

$$
x_{u,i}+x_{v,j}\le1
\qquad \forall |i-j|\le1.
$$

This directly forbids all assignments with $|f(u)-f(v)|<2$ and requires no auxiliary direction variable.

### Distance-Two Separation

For every $(u,v)\in E_2$ and each label $k$, add

$$
x_{u,k}+x_{v,k}\le1.
$$

This forbids equal labels at graph distance two.

### Symmetry Breaking

The current implementation fixes the first vertex to label zero:

$$
x_{v_0,0}=1.
$$

This removes label-translation symmetry while preserving the existence of an optimal labeling.

### Warm Start and Decoding

The greedy labeling is converted into binary values by setting exactly one $x_{v,k}$ to one for each vertex. After optimization, the selected binary variable for each vertex is decoded into a labeling dictionary and checked independently by `src/core/validator.py`.

## 4. Comparison

| Criterion | Big-M formulation | Binary assignment formulation |
| --- | --- | --- |
| Primary variables | Integer labels $f_v$ and binary direction variables | Binary assignment variables $x_{v,k}$ and span $\lambda$ |
| Constraint strength | Depends on the choice of $M$; loose $M$ can weaken the LP relaxation | Direct forbidden-pair constraints; no Big-M coefficient is needed |
| Model size | Usually fewer variables and constraints for small $U$ | $|V|(U+1)$ assignment variables, with potentially many pair constraints |
| Numerical behavior | Sensitive to excessively large $M$ | Generally cleaner because constraints use small coefficients |
| Interpretability | Compact and natural for integer-label models | Explicitly represents every vertex-label decision |
| Solver trade-off | Often faster on compact instances | May provide stronger combinatorial structure but grow quickly with $U$ |

Gurobi and CPLEX can solve both models as mixed-integer programs. The most suitable formulation depends on graph size, upper bound, solver presolve, and the quality of the greedy warm start. The benchmark runner supports `--formulation assignment`, `--formulation big-m`, and `--formulation both` for empirical comparison.
