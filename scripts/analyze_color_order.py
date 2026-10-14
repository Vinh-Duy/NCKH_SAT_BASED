"""Reproducible post-hoc color-order constructions on the entire v2 cohort.

The original solver observations and clique audit are immutable inputs.
Successful constructions supply witnesses, never timed SAT/ILP successes.
"""
import argparse
import copy
import csv
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
from scripts.construct_color_order import construct, verify_order
from scripts.verify_clique_certificate import graph_digest, verify, verify_file

BASE = ROOT/'results/analysis/clique_certificates/cc0e412739ccc8d2'
EVIDENCE = ROOT/'results/analysis/evidence_summary/0700e674e1e6ba4e'


def read_csv(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def retained_certificate(original, proposal):
    """Keep the better independently checked witness, without source confusion."""
    baseline = verify(original)
    if proposal['status'] not in {'UNKNOWN', 'FEASIBLE'}:
        raise ValueError('construction must report FEASIBLE or UNKNOWN')
    if proposal['status'] == 'UNKNOWN':
        if proposal['labels'] is not None:
            raise ValueError('UNKNOWN construction must not supply labels')
        return copy.deepcopy(original), False
    labels = proposal['labels']
    if (not isinstance(labels, dict)
            or any(type(v) is not int or type(a) is not int or a < 0
                   for v, a in labels.items())):
        raise ValueError('construction labels must map integer vertices to nonnegative integers')
    for name in ('span', 'seed', 'attempts'):
        value = proposal[name]
        if type(value) is not int or value < 0:
            raise ValueError(f'construction {name} must be a nonnegative integer')
    if proposal['attempts'] > 100:
        raise ValueError('construction attempts exceed the fixed budget')
    proof = verify_order(original['graph']['n'], original['graph']['edges'],
                         proposal['classes'], proposal['order'], original['h'], original['k'])
    if (proposal['labels'] != dict(enumerate(proof['labels']))
            or proposal['span'] != proof['span']):
        raise ValueError('construction witness differs from checked order')
    candidate = copy.deepcopy(original)
    candidate.update(labels=proof['labels'], upper_bound=proof['span'])
    verify(candidate)
    if proof['span'] >= baseline['upper_bound']:
        return copy.deepcopy(original), False
    candidate.pop('source_observation', None)
    candidate.pop('source_status', None)
    candidate.update(source_kind='posthoc_color_order', source_status='FEASIBLE',
                     construction=dict(classes=copy.deepcopy(proposal['classes']),
                                       order=list(proposal['order']),
                                       seed=proposal['seed'], attempts=proposal['attempts']))
    return candidate, True


def analyze(seed=0, max_restarts=100):
    old = {c['id']: c for c in map(json.loads, (BASE/'certificates.jsonl').read_text().splitlines())}
    previous = read_csv(BASE/'instances.csv')
    evidence = {r['Certificate_ID']: r for r in read_csv(EVIDENCE/'instances.csv')}
    if set(old) != set(evidence) or len(previous) != len(old):
        raise ValueError('baseline certificate/cohort mismatch')
    graphs = {name: graph for name, _, graph in general_pilot()}
    rows, certificates, candidates = [], [], []
    for row in previous:
        key = row['Certificate_ID']
        certificate = old[key]
        graph = graphs[row['Instance']]
        canonical = dict(n=len(graph), edges=sorted([min(u, v), max(u, v)] for u, v in graph.edges()))
        if certificate['graph_sha256'] != graph_digest(canonical):
            raise ValueError('regenerated graph differs from archived certificate')
        h, k = int(row['h']), int(row['k'])
        if (certificate['h'], certificate['k']) != (h, k):
            raise ValueError('parameter mismatch')
        proposal = construct(graph, h, k, seed=seed, max_restarts=max_restarts)
        retained, improved = retained_certificate(certificate, proposal)
        candidates.append(dict(id=key, proposal=proposal))
        verified = verify(retained)
        low, old_upper = int(row['Augmented_LB']), int(row['Witness_UB'])
        upper = verified['upper_bound']
        if low > upper:
            raise ValueError('new witness contradicts archived lower bound')
        baseline = evidence[key]
        if (int(baseline['Final_LB']), int(baseline['Witness_UB'])) != (low, old_upper):
            raise ValueError('consolidated baseline mismatch')
        rows.append(dict(Instance=row['Instance'], Group=row['Group'], h=h, k=k, V=len(graph),
            Theory=int(baseline['Theory']), Other_Closed=int(baseline['Other_Closed']),
            Open_Before=int(baseline['Open_Before']),
            Before_Construction_LB=low, Before_Construction_UB=old_upper,
            Construction_Status=proposal['status'], Construction_Span=proposal.get('span'),
            Class_Count=proposal['class_count'], Attempts=proposal['attempts'],
            Improved_UB=improved, Final_LB=low, Final_UB=upper, Final_Gap=upper-low,
            Clique_Certified=verified['optimal'],
            Newly_Closed=low < old_upper and low == upper,
            Closed_After=low == upper, Open_After=low < upper,
            Certificate_ID=key, Witness_Source='construction' if improved else 'archived_v2'))
        certificates.append(retained)
    if len(rows) != 117 or len({r['Certificate_ID'] for r in rows}) != 117:
        raise ValueError('expected all 117 distinct instances')
    return rows, certificates, candidates


def summary_rows(rows):
    keys = ('Theory', 'Other_Closed', 'Open_Before', 'Clique_Certified',
            'Newly_Closed', 'Closed_After', 'Open_After', 'Improved_UB')
    result = []
    for group, h, k in sorted({(r['Group'], r['h'], r['k']) for r in rows}):
        subset = [r for r in rows if (r['Group'], r['h'], r['k']) == (group, h, k)]
        result.append(dict(Group=group, h=h, k=k, Instances=len(subset),
                           **{key: sum(r[key] for r in subset) for key in keys}))
    result.append(dict(Group='ALL', h='', k='', Instances=len(rows),
                       **{key: sum(r[key] for r in rows) for key in keys}))
    return result


def export(output_root):
    manifests = {}
    for directory in (BASE, EVIDENCE):
        manifest = json.loads((directory/'sources.json').read_text())
        verify_cache(directory, manifest['identity'])
        manifests[str(directory.relative_to(ROOT))] = digest(directory/'sources.json')
    base_identity = json.loads((BASE/'sources.json').read_text())['identity']
    for name, expected in base_identity['inputs'].items():
        if digest(ROOT/name) != expected:
            raise ValueError('raw input fingerprint mismatch')
    if nx.__version__ != base_identity['networkx']:
        raise ValueError('NetworkX differs from archived graph generator')
    sources = [Path(__file__), ROOT/'scripts/construct_color_order.py',
               ROOT/'scripts/verify_clique_certificate.py', ROOT/'scripts/build_confirmation_report.py',
               *ROOT.glob('benchmarks/*.py'), *ROOT.glob('src/**/*.py')]
    identity = dict(kind='posthoc-color-order-v1', seed=0, max_restarts=100,
                    networkx=nx.__version__, python=sys.version, reports=manifests,
                    sources={str(p.resolve().relative_to(ROOT)): digest(p) for p in sorted(set(sources))})
    version = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16]
    output_root.mkdir(parents=True, exist_ok=True)
    output = output_root/version
    if output.exists():
        verify_cache(output, identity)
        verify_file(output/'certificates.jsonl')
        return output
    rows, certificates, candidates = analyze()
    summary = summary_rows(rows)
    counts = dict(ConstructionInstances=len(rows), ConstructionClosed=summary[-1]['Closed_After'],
        ConstructionOpen=summary[-1]['Open_After'], ConstructionNewlyClosed=summary[-1]['Newly_Closed'],
        ConstructionImproved=summary[-1]['Improved_UB'],
        ConstructionCliqueCertified=summary[-1]['Clique_Certified'],
        ConstructionTotalNewlyClosed=summary[-1]['Closed_After']-summary[-1]['Theory']-summary[-1]['Other_Closed'],
        ConstructionCandidates=sum(r['Construction_Status'] == 'FEASIBLE' for r in rows),
        ConstructionUnknown=sum(r['Construction_Status'] == 'UNKNOWN' for r in rows))
    temporary = Path(tempfile.mkdtemp(prefix='.building-', dir=output_root))
    try:
        write_csv(temporary/'instances.csv', rows)
        write_csv(temporary/'summary.csv', summary)
        for name, selected in [('newly_closed', [r for r in rows if r['Newly_Closed']]),
                               ('unresolved', [r for r in rows if r['Open_After']])]:
            with (temporary/f'{name}.csv').open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(selected)
        (temporary/'certificates.jsonl').write_text(''.join(json.dumps(c, sort_keys=True)+'\n' for c in certificates))
        (temporary/'candidates.jsonl').write_text(''.join(json.dumps(c, sort_keys=True)+'\n' for c in candidates))
        verify_file(temporary/'certificates.jsonl')
        (temporary/'counts.tex').write_text(''.join(f'\\newcommand{{\\{key}}}{{{value}}}\n' for key, value in counts.items()))
        lines = [r'\begin{tabular}{@{}llrrrrrrr@{}}', r'\toprule',
                 r'& & & \multicolumn{3}{c}{Original v2 evidence} & \multicolumn{3}{c}{After certification}\\',
                 r'\cmidrule(lr){4-6}\cmidrule(l){7-9}',
                 r'Family & $(h,k)$ & Cases & Theory & Other & Open & Clique-cert. & Closed & Open\\', r'\midrule']
        for row in summary:
            if row['Group'] == 'ALL':
                lines.append(r'\midrule')
            family = {'tree':'Tree', 'PxP':r'$P_n\square P_m$', 'ALL':'Total'}.get(row['Group'], row['Group'])
            pair = '--' if row['Group'] == 'ALL' else f"$({row['h']},{row['k']})$"
            lines.append(' & '.join([family, pair, *[str(row[key]) for key in
                ('Instances', 'Theory', 'Other_Closed', 'Open_Before', 'Clique_Certified', 'Closed_After', 'Open_After')]])+r'\\')
        (temporary/'summary.tex').write_text('\n'.join([*lines, r'\bottomrule', r'\end{tabular}'])+'\n')
        lines = [r'\begin{tabular}{rrrrrrr}', r'\toprule',
                 r'$n$ & $p$ & Seed & $(h,k)$ & Saved $[L,U]$ & $|Q|$ & Optimum\\', r'\midrule']
        for row in rows:
            if row['Newly_Closed']:
                name = row['Instance']
                if not name.startswith('ER_'):
                    raise ValueError('new closure outside reviewed ER table scope')
                p, seed = name.split('_p')[1].split('_seed')
                certificate = next(c for c in certificates if c['id'] == row['Certificate_ID'])
                lines.append(f"{row['V']} & {p} & {seed} & $({row['h']},{row['k']})$ & "
                    f"$[{row['Before_Construction_LB']},{row['Before_Construction_UB']}]$ & "
                    f"{len(certificate['clique'])} & {row['Final_UB']}"+r'\\')
        (temporary/'closures.tex').write_text('\n'.join([*lines,r'\bottomrule',r'\end{tabular}'])+'\n')
        (temporary/'README.md').write_text(f'''# Color-order constructions and optimality certificates

All 117 v2 graph/parameter instances were attempted using seed 0 and at most
100 insertion attempts. This is a post-hoc witness construction, not an SAT/ILP
rerun or a controlled runtime comparison. The sparse-pair class builder is
heuristic and need not find a minimum coloring. UNKNOWN does not mean infeasible.

For 0 < k <= h <= 2k, square-independent color classes can be assigned labels
0,k,2k,... if consecutive classes share no original edge when h>k. A matching
in the complement of G^2 yields pair classes; unmatched vertices are singleton
classes. A bounded seeded insertion search orders them. Every returned witness
is checked from the partition/order and independently from original graph distances.
Matching optimality and Hamiltonian-path nonexistence are not needed or certified.

## Results

- Constructed valid candidates: {counts['ConstructionCandidates']}; UNKNOWN: {counts['ConstructionUnknown']}.
- Improved saved upper bounds: {counts['ConstructionImproved']}.
- Newly closed relative to the previous 98 closed/19 open analysis: {counts['ConstructionNewlyClosed']}.
- Combined evidence now closes {counts['ConstructionClosed']}/117; {counts['ConstructionOpen']} remain open.
- Clique-plus-labeling certificates alone establish {counts['ConstructionCliqueCertified']} optima.
  This overlaps the combined closed count and must not be added to it.

## Files and definitions

- instances.csv: one row per instance; Before_Construction_LB/UB are the immutable
  October 9 clique-augmented interval. Final_LB is unchanged; Final_UB is the smaller
  of the stored witness and a checked construction. Final_Gap = Final_UB - Final_LB.
  Improved_UB and Newly_Closed are different properties. Witness_Source distinguishes
  fresh constructions from archived v2 witnesses; no new label is attributed to a solver.
- summary.csv: 15 family/(h,k) rows and one ALL row. Do not add ALL to the group rows.
  Theory/Other_Closed/Open_Before are the original v2 classifications before all
  structural certification; Clique_Certified overlaps earlier closures.
- newly_closed.csv, unresolved.csv: subsets for follow-up; not selected benchmark cohorts.
- candidates.jsonl: all attempted configurations, classes, orders, labels, statuses,
  and attempt counts. A successful candidate can be worse than an archived witness.
- certificates.jsonl: the best retained labeling paired with the existing square clique.
  Every record uses the standalone verifier's original schema, which needs only stdlib.
  Matching source-observation fields are removed when a construction replaces a witness.
- summary.tex, closures.tex, counts.tex: manuscript outputs.
- sources.json: original report, implementation, and output fingerprints and configuration.

The final combined intervals still rely on saved solver lower bounds where stronger
than the clique bound. Only a matching mathematical bound provides independent
optimality certification. The sufficient condition is proved in the manuscript;
neither this construction nor using SAT for labeling is claimed to be first in the literature.
No universal formula, general performance ranking, or additional timed solver win follows.
''')
        (temporary/'sources.json').write_text(json.dumps(dict(identity=identity, counts=counts,
            outputs_sha256={p.name:digest(p) for p in temporary.iterdir()}), indent=2)+'\n')
        temporary.rename(output)
    except BaseException:
        shutil.rmtree(temporary)
        raise
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', type=Path, default=ROOT/'results/analysis/color_order')
    parser.add_argument('--publish', action='store_true')
    args = parser.parse_args()
    output = export(args.output_root)
    if args.publish:
        relative = output.resolve().relative_to(ROOT).as_posix()
        (ROOT/'paper/generated/color_order.tex').write_text(
            '% Generated by scripts/analyze_color_order.py --publish\n'
            f'\\input{{{relative}/counts.tex}}\n'
            f'\\newcommand{{\\ConstructionReportDir}}{{{relative}}}\n')
    print(output)
