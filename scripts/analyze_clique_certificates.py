"""Post-hoc square-clique certificates for the complete v2 confirmation.

Audits all 117 instances, not a selected success subset. Does not run SAT/ILP,
modify solver observations, or add post-hoc work to timed success counts.
"""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import networkx as nx
from benchmarks.general_suite import general_pilot
from scripts.build_confirmation_report import digest, verify_cache, write_csv
from scripts.summarize_progress_run import collect
from scripts.verify_clique_certificate import graph_digest, verify, verify_file

DEFAULT_INPUT = ROOT/'results/runs/general_progress_v2_20261007T062406751526Z.csv'


def largest_square_clique(graph):
    """Deterministic tie-breaking; enumeration is exponential in the worst case.

Only clique membership, not maximality or maximum size, is needed for a proof.
Keep one candidate at a time rather than materializing all maximal cliques.
"""
    best = []
    for clique in nx.find_cliques(nx.power(graph, 2)):
        candidate = sorted(clique)
        if len(candidate) > len(best) or len(candidate) == len(best) and candidate < best:
            best = candidate
    return best


def analyze(path):
    checked, instances, _, _, _ = collect(path)
    records = {r['Graph']: r for r in map(json.loads, path.with_suffix('.witnesses.jsonl').read_text().splitlines())}
    graphs = {name: graph for name, _, graph in general_pilot()}
    cliques = {name: largest_square_clique(graph) for name, graph in graphs.items()}
    rows, certificates = [], []
    for instance in instances:
        name, h, k = (instance[key] for key in ('Instance', 'h', 'k'))
        observations = [r for r in checked if (r['Instance'], r['h'], r['k']) == (name, h, k)]
        selected = min(observations, key=lambda r: (r['Witness_Span'], r['Graph']))
        record = records[selected['Graph']]
        graph = graphs[name]
        if set(graph) != set(range(len(graph))):
            raise ValueError('certificate export requires integer vertex indices 0..n-1')
        embedded = dict(n=len(graph), edges=sorted([min(u, v), max(u, v)] for u, v in graph.edges()))
        configuration = record['configuration']
        if (set(configuration['vertices']) != set(graph)
                or sorted(sorted(edge) for edge in configuration['edges']) != embedded['edges']
                or (configuration['h'], configuration['k']) != (h, k)):
            raise ValueError('selected witness graph or parameter mismatch')
        labeling = {ast.literal_eval(v): a for v, a in record['result']['labels']}
        certificate = dict(schema='lhk-square-clique-v1', id=f'{name}__h{h}_k{k}',
                           instance=name, h=h, k=k, graph=embedded,
                           graph_sha256=graph_digest(embedded), clique=cliques[name],
                           labels=[labeling[v] for v in range(len(graph))],
                           lower_bound=min(h, k)*max(0, len(cliques[name])-1),
                           upper_bound=selected['Witness_Span'],
                           source_observation=selected['Graph'], source_status=selected['Status'])
        proof = verify(certificate)
        original_lb, upper = instance['Combined_LB'], instance['Best_Witness_Span']
        if upper != proof['upper_bound']:
            raise ValueError('selected witness is not the best saved witness')
        combined = max(original_lb, proof['lower_bound'])
        if combined > upper:
            raise ValueError('post-hoc lower bound contradicts a saved witness')
        rows.append(dict(Instance=name, Group=instance['Group'], h=h, k=k, V=len(graph),
                         Original_LB=original_lb, Witness_UB=upper,
                         Clique_Size=len(cliques[name]), Clique_LB=proof['lower_bound'],
                         Augmented_LB=combined, Original_Gap=upper-original_lb,
                         Augmented_Gap=upper-combined, Clique_Optimal=proof['optimal'],
                         Newly_Closed=original_lb < upper and proof['optimal'],
                         Certificate_ID=certificate['id'], Witness_Observation=selected['Graph']))
        certificates.append(certificate)
    return rows, certificates


def export(path, output_root):
    path = Path(path).resolve()
    inputs = [path, path.with_suffix('.metadata.json'), path.with_suffix('.witnesses.jsonl')]
    # Include all implementation dependencies of the existing cohort audit.
    sources = sorted({Path(__file__).resolve(), ROOT/'scripts/verify_clique_certificate.py',
                      ROOT/'scripts/summarize_progress_run.py', ROOT/'scripts/build_confirmation_report.py',
                      ROOT/'scripts/audit_general_pilot.py', ROOT/'scripts/compare_unresolved_bounds.py',
                      *ROOT.glob('src/**/*.py'), *ROOT.glob('benchmarks/*.py')})
    identity = dict(kind='post-hoc-square-clique-v1', networkx=nx.__version__,
                    inputs={str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p): digest(p) for p in inputs},
                    analysis_sources={str(p.relative_to(ROOT)): digest(p) for p in sources})
    version = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16]
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    output = output_root/version
    if output.exists():
        verify_cache(output, identity)
        verify_file(output/'certificates.jsonl')
        return output
    rows, certificates = analyze(path)
    counts = dict(CliqueInstances=len(rows), CliqueOriginalClosed=sum(r['Original_Gap'] == 0 for r in rows),
                  CliqueAugmentedClosed=sum(r['Augmented_Gap'] == 0 for r in rows),
                  CliqueRemainingOpen=sum(r['Augmented_Gap'] > 0 for r in rows),
                  CliqueNewlyClosed=sum(r['Newly_Closed'] for r in rows),
                  CliqueImproved=sum(r['Augmented_LB'] > r['Original_LB'] for r in rows),
                  CliqueIndependentOptima=sum(r['Clique_Optimal'] for r in rows))
    temporary = Path(tempfile.mkdtemp(prefix='.building-', dir=output_root))
    try:
        write_csv(temporary/'instances.csv', rows)
        write_csv(temporary/'originally_open.csv', [r for r in rows if r['Original_Gap'] > 0])
        write_csv(temporary/'summary.csv', [counts])
        (temporary/'certificates.jsonl').write_text(''.join(json.dumps(c, sort_keys=True)+'\n' for c in certificates))
        verify_file(temporary/'certificates.jsonl')
        (temporary/'counts.tex').write_text(''.join(f'\\newcommand{{\\{key}}}{{{value}}}\n' for key, value in counts.items()))
        lines = [r'\begin{tabular}{rrrrrr}', r'\toprule',
                 r'$n$ & $p$ & Seed & $|Q|$ & Saved interval & Certified value\\', r'\midrule']
        for row in rows:
            if row['Newly_Closed']:
                name = row['Instance']
                if not name.startswith('ER_') or (row['h'], row['k']) != (3, 2):
                    raise ValueError('newly closed case outside the reviewed table scope')
                p, seed = name.split('_p')[1].split('_seed')
                lines.append(f"{row['V']} & {p} & {seed} & {row['Clique_Size']} & "
                             f"$[{row['Original_LB']},{row['Witness_UB']}]$ & {row['Witness_UB']}"+r'\\')
        (temporary/'closures.tex').write_text('\n'.join([*lines, r'\bottomrule', r'\end{tabular}'])+'\n')
        (temporary/'README.md').write_text(f'''# Post-hoc square-clique certificates

Source: `{path.name}` (complete isolated-progress-v2 confirmation only).
All {len(rows)} graph/parameter instances are included. The earlier interrupted run is excluded.

For a clique Q in the square of the original graph, every pair has distance at most two.
Thus lambda(h,k) >= min(h,k) (|Q|-1). Sorting the labels proves this bound directly.
A valid labeling with matching span proves optimality without trusting solver lower bounds.
This elementary bound is not claimed as a new general theorem.

- Independently certified optima using the clique bound alone: {counts['CliqueIndependentOptima']}.
- Pooled solver intervals closed before this analysis: {counts['CliqueOriginalClosed']}.
- Improved lower bounds: {counts['CliqueImproved']}; newly closed intervals: {counts['CliqueNewlyClosed']}.
- Closed after combining evidence: {counts['CliqueAugmentedClosed']}; still open: {counts['CliqueRemainingOpen']}.

## Files and interpretation

- `certificates.jsonl`: one self-contained certificate per instance; graph order `n`, sorted edges,
  clique vertex indices, complete labeling indexed by vertex, h/k, graph fingerprint,
  and selected source observation. Vertex indices are 0..n-1, including isolates.
  The checker certifies the embedded graph. The generator separately binds it to the audited
  experiment graph and witness. Source file hashes are in `sources.json`.
- `instances.csv`: all instances. `Original_LB` is the maximum saved lower bound across six
  observations; `Witness_UB` is the smallest validated saved span. `Clique_LB` is independently
  checked, and `Augmented_LB=max(Original_LB,Clique_LB)`. Gaps are absolute label units (UB-LB).
  `Clique_Optimal` requires the clique bound alone to equal UB. `Newly_Closed` additionally
  requires the original pooled interval to have been open. Certificate and observation IDs link evidence.
- `originally_open.csv`: the same columns for the original 21 open instances; not a new cohort.
- `summary.csv`, `counts.tex`, `closures.tex`: machine-readable counts and manuscript tables.
- `sources.json`: immutable input/source/output SHA-256 fingerprints and NetworkX version.

The generator enumerates maximal cliques and chooses a largest one with lexicographic
tie-breaking. This is exponential in the worst case and is only a post-hoc analysis of this
39-graph cohort (20--60 vertices), not an asserted scalable solver improvement. Maximum
clique size is not needed to verify any certificate. The standalone verifier uses only the
Python standard library, checks graph structure, all relevant label constraints, clique membership,
and the derived bounds. It does not verify SAT UNSAT proofs or ILP dual certificates.

Original statuses, timings, 30-second coverage, and raw files are unchanged. Augmented intervals
that rely on Original_LB still rely on saved solver claims. Repetitions are not independent graphs.
These instance-specific results neither prove a formula for all random graphs nor SAT/ILP equivalence.
''')
        (temporary/'sources.json').write_text(json.dumps(dict(identity=identity, counts=counts,
            outputs_sha256={p.name: digest(p) for p in temporary.iterdir()}), indent=2)+'\n')
        temporary.rename(output)
    except BaseException:
        shutil.rmtree(temporary)
        raise
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=DEFAULT_INPUT)
    parser.add_argument('--output-root', type=Path, default=ROOT/'results/analysis/clique_certificates')
    parser.add_argument('--publish', action='store_true', help='select verified outputs in the manuscript wrapper')
    args = parser.parse_args()
    output = export(args.input, args.output_root)
    if args.publish:
        relative = output.resolve().relative_to(ROOT).as_posix()
        (ROOT/'paper/generated/clique_certificates.tex').write_text(
            '% Generated by scripts/analyze_clique_certificates.py --publish\n'
            f'\\input{{{relative}/counts.tex}}\n'
            f'\\newcommand{{\\CliqueReportDir}}{{{relative}}}\n')
    print(output)
