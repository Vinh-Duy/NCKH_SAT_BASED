"""Supplemental matching-bound audit of the unchanged 117-instance cohort.

Generation uses NetworkX. --verify-only checks the saved matching certificates,
original witnesses, and classifications using only the standard library.
"""
import argparse
import copy
import csv
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.certificate_support import classify
from scripts.matching_bound_certificate import generate, verify
from scripts.audit_certificate_validation import digest, records, read_csv, write_csv

SOURCE = ROOT/'results/analysis/color_order/2d62af353a1756ae'
DEFAULT = ROOT/'results/analysis/matching_bounds/v1_20261017'


def classifications(certificates, old_rows, proofs):
    support = classify(list(certificates.values()), old_rows)
    by_id = {r['Certificate_ID']:r for r in old_rows}
    rows = []
    if set(proofs) - set(certificates):
        raise ValueError('unexpected matching certificate')
    for r in support:
        key = r['Certificate_ID']
        c = certificates[key]
        proof = proofs.get(key)
        bound = None
        if proof is not None:
            if (proof['graph'],proof['h'],proof['k'],proof['labels']) != (c['graph'],c['h'],c['k'],c['labels']):
                raise ValueError('matching certificate differs from historical graph or witness')
            bound = verify(proof)['lower_bound']
        combined = max(r['Mathematical_LB'],bound or 0)
        upper = r['Witness_UB']
        if combined > upper:
            raise ValueError('new bound contradicts historical witness')
        rows.append(dict(Certificate_ID=key,Instance=r['Instance'],Group=r['Group'],h=r['h'],k=r['k'],
            Eligible=proof is not None,Matching_LB=bound,
            Previous_Mathematical_LB=r['Mathematical_LB'],Combined_Mathematical_LB=combined,
            Witness_UB=upper,Previous_Final_LB=int(by_id[key]['Final_LB']),
            Previous_Closed=r['Closed'],Previous_Independent=r['Independent_Optimal'],
            Improved_Mathematical_LB=combined > r['Mathematical_LB'],
            Matching_Certified=bound==upper,Independent_After=combined==upper,
            Newly_Independent=combined==upper and not r['Independent_Optimal'],
            Newly_Closed=combined==upper and not r['Closed']))
    return rows


def totals(rows):
    return dict(instances=len(rows),eligible=sum(r['Eligible'] for r in rows),
        improved_mathematical_bounds=sum(r['Improved_Mathematical_LB'] for r in rows),
        matching_certified=sum(r['Matching_Certified'] for r in rows),
        independently_certified_after=sum(r['Independent_After'] for r in rows),
        newly_independent=sum(r['Newly_Independent'] for r in rows),
        newly_closed=sum(r['Newly_Closed'] for r in rows))


def build(output):
    import networkx as nx
    certificates = records(SOURCE/'certificates.jsonl', 'id')
    old_rows = read_csv(SOURCE/'instances.csv')
    cache, proofs = {}, {}
    for key,c in certificates.items():
        fingerprint = c['graph_sha256']
        if fingerprint not in cache:
            graph = nx.Graph()
            graph.add_nodes_from(range(c['graph']['n']))
            graph.add_edges_from(c['graph']['edges'])
            cache[fingerprint] = generate(graph, 1, 1)
        template = cache[fingerprint]
        if template is not None:
            proof = copy.deepcopy(template)
            proof.update(id=key,instance=c['instance'],h=c['h'],k=c['k'],
                lower_bound=c['k']*max(0,template['square_chromatic']-1),
                labels=c['labels'],upper_bound=c['upper_bound'])
            verify(proof)
            proofs[key] = proof
    rows = classifications(certificates,old_rows,proofs)
    output.mkdir(parents=True,exist_ok=False)
    write_csv(output/'instances.csv',rows)
    (output/'certificates.jsonl').write_text(''.join(json.dumps(c,sort_keys=True)+'\n' for c in proofs.values()))
    source = dict(input_hashes={str(p.relative_to(ROOT)):digest(p) for p in (SOURCE/'certificates.jsonl',SOURCE/'instances.csv')},
        source_hashes={p:digest(ROOT/p) for p in ('scripts/analyze_matching_bounds.py',
            'scripts/matching_bound_certificate.py','scripts/verify_clique_certificate.py',
            'scripts/certificate_support.py')},
        output_hashes={p.name:digest(p) for p in output.iterdir()},totals=totals(rows))
    (output/'sources.json').write_text(json.dumps(source,sort_keys=True,indent=2)+'\n')
    return source['totals']


def audit(output):
    source = json.loads((output/'sources.json').read_text())
    for name,expected in source['input_hashes'].items():
        if digest(ROOT/name) != expected:
            raise ValueError('historical input changed')
    for name,expected in source['output_hashes'].items():
        if digest(output/name) != expected:
            raise ValueError('audit output changed')
    certificates = records(SOURCE/'certificates.jsonl','id')
    proofs = records(output/'certificates.jsonl','id')
    # Verify that unsupported cases were not selected out of this audit.
    for key,c in certificates.items():
        adjacency = [set() for _ in range(c['graph']['n'])]
        for u,v in c['graph']['edges']:
            adjacency[u].add(v)
            adjacency[v].add(u)
        complement = [{v for v in range(len(adjacency)) if v != u and v not in adjacency[u]
                       and not adjacency[u] & adjacency[v]} for u in range(len(adjacency))]
        eligible = not any(complement[u] & complement[v] for u in range(len(adjacency)) for v in complement[u])
        if eligible != (key in proofs):
            raise ValueError('structurally eligible cohort mismatch')
    rows = classifications(certificates,read_csv(SOURCE/'instances.csv'),proofs)
    expected_rows = [{k:'' if v is None else str(v) for k,v in r.items()} for r in rows]
    if read_csv(output/'instances.csv') != expected_rows or totals(rows) != source['totals']:
        raise ValueError('classification differs from checked certificates')
    return totals(rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=DEFAULT)
    parser.add_argument('--verify-only',action='store_true')
    args = parser.parse_args()
    print(json.dumps(audit(args.output) if args.verify_only else build(args.output),indent=2))
