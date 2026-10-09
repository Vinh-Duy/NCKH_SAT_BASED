# Independent square-clique certificates

This analysis supplies mathematical lower bounds for existing L(h,k)
labelings. It is separate from the timed SAT and assignment ILP experiments.

## Bound and proof

Let Q be a set of vertices with distance at most two between every distinct
pair in the original simple undirected graph G. Equivalently, Q is a clique
of the square graph G². For nonnegative integer h,k,

\[
\lambda_{h,k}(G)\geq\min(h,k)\max\{0,|Q|-1\}.
\]

For |Q|≥2, sort the labels on Q. Every consecutive pair differs by at least
min(h,k), because its vertices are at distance one or two. Summing the |Q|−1
gaps gives the bound. The empty/singleton case has lower bound zero. A valid
labeling whose span matches this bound proves optimality. In the primary
domain h≥k≥1 the bound is k(|Q|−1) for nonempty Q. This is an elementary
packing argument, not a claim of a new general theorem.

Distance is measured in G, not in the induced subgraph on Q: an intermediate
vertex may lie outside Q. Adjacent vertices use h even if they have a common
neighbor; this matters when h<k. Disconnected graphs and isolates are retained.

## Evidence and trust boundary

`scripts/analyze_clique_certificates.py` audits the complete v2 confirmation
before deriving certificates for all 117 graph/parameter instances. It uses
NetworkX to enumerate maximal cliques of each square graph and selects a
largest one, with deterministic lexicographic tie-breaking. Enumeration can
take exponential time; the current cohort contains only 39 graphs of 20–60
vertices. See the [official iterator documentation](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.clique.find_cliques.html).
The analysis is not a scalable algorithm claim or a timed solver improvement.

`scripts/verify_clique_certificate.py` uses only the Python standard library.
It validates the embedded graph, clique membership, every label constraint,
and the resulting bounds. It does not trust the generator's maximum-clique
claim: any valid clique suffices. It does not import the model encoder,
model validator, a graph library, or a solver. `python -S` can run the checker
without installed site packages. Its tests include all three-vertex simple
graphs against a separate shortest-path oracle, h<k, zero separations,
disconnected vertices, incomplete witnesses, and tampered proof objects.

The certificate contains the original graph explicitly, so standalone
verification is a statement about that graph. The generator separately binds
the graph and h,k to the source experiment configuration and validates the
chosen stored witness. `sources.json` records input, implementation, and output
SHA-256 hashes; the NetworkX version must match the saved generator version.
Hashes detect changes relative to the manifest, not authenticity against a
malicious replacement of the entire bundle. Source observation identifiers and
statuses remain available for tracing the chosen labelings.

## Reporting rules and findings

The original pooled interval is [max saved LB, min validated witness span]
over the six v2 observations for an instance. The augmented interval replaces
its lower bound with max(saved LB, clique LB). When the clique bound alone
equals the witness span, optimality is independently established without
trusting the solver lower bound. Other augmented closures may still rely on
saved solver claims. No DRAT/LRAT or Gurobi dual certificate is checked here.

The reviewed analysis improves 15 lower bounds and closes two additional
instances: ER(40,0.30,seed1), L(3,2), span 64; and ER(60,0.30,seed1),
L(3,2), span 110. Both selected matching witnesses are Gurobi repetition-0
FEASIBLE incumbents. Fifty of all 117 instances have matching clique bounds
and witnesses, including these two. Combining all evidence closes 98/117 and
leaves 19 open. These findings are instance-specific, not a formula for an
entire random graph family. They do not increase timed SAT or ILP success counts.

See the [versioned results and column definitions](../../results/analysis/clique_certificates/README.md).
