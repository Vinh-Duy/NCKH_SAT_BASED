"""Classify mathematical support without trusting recorded solver bounds.

Uses only the standard library and the standalone clique/labeling verifier.
A grid reference is used only after checking its entire indexed edge set.
"""

import argparse
import csv
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.verify_clique_certificate import verify


def mathematical_support(certificate):
    checked = verify(certificate)
    n = certificate['graph']['n']
    edges = certificate['graph']['edges']
    h, k = certificate['h'], certificate['k']
    degrees = [0] * n
    for u, v in edges:
        degrees[u] += 1
        degrees[v] += 1
    delta = max(degrees, default=0)
    degree_bound = h + (delta - 1) * min(h, k) if delta else 0
    # The reference theorem uses the standard row-major grid indexing.
    # A matching name alone is never sufficient to apply the formula.
    grid_bound = 0
    match = re.fullmatch(r'P_(\d+)xP_(\d+)', certificate['instance'])
    if match and (h, k) == (2, 1):
        a, b = map(int, match.groups())
        if min(a, b) >= 4 and n == a * b:
            grid_edges = {(i*b+j, i*b+j+1) for i in range(a) for j in range(b-1)}
            grid_edges |= {(i*b+j, (i+1)*b+j) for i in range(a-1) for j in range(b)}
            if {tuple(e) for e in edges} == grid_edges:
                grid_bound = 6
    theory_bound = max(degree_bound, grid_bound)
    mathematical_bound = max(theory_bound, checked['lower_bound'])
    upper = checked['upper_bound']
    if mathematical_bound > upper:
        raise ValueError('mathematical bound contradicts validated witness')
    return dict(Theory_Bound=theory_bound, Clique_Bound=checked['lower_bound'],
                Mathematical_LB=mathematical_bound, Witness_UB=upper,
                Theory_Attained=theory_bound == upper,
                Clique_Attained=checked['optimal'],
                Independent_Optimal=mathematical_bound == upper)


def classify(certificates, instances):
    by_id = {}
    for c in certificates:
        if not c.get('id') or c['id'] in by_id:
            raise ValueError('missing or duplicate certificate ID')
        by_id[c['id']] = c
    rows, seen = [], set()
    for row in instances:
        key = row['Certificate_ID']
        if key in seen or key not in by_id:
            raise ValueError('duplicate or missing instance certificate')
        seen.add(key)
        c = by_id[key]
        if (row['Instance'], int(row['h']), int(row['k']), int(row['V'])) != (
                c['instance'], c['h'], c['k'], c['graph']['n']):
            raise ValueError('instance/graph/parameter mismatch')
        support = mathematical_support(c)
        low, high = int(row['Final_LB']), int(row['Final_UB'])
        if high != support['Witness_UB'] or not 0 <= low <= high:
            raise ValueError('recorded interval differs from checked witness')
        closed = low == high
        if str(row['Closed_After']) != str(closed):
            raise ValueError('recorded closure flag disagrees with interval')
        if support['Independent_Optimal'] and not closed:
            raise ValueError('mathematically closed instance recorded as open')
        if int(row['Theory']) != int(support['Theory_Attained']):
            raise ValueError('theory classification differs from checked graph')
        if str(row['Clique_Certified']) != str(support['Clique_Attained']):
            raise ValueError('clique classification differs from checked certificate')
        rows.append(dict(Certificate_ID=key, Instance=row['Instance'], Group=row['Group'],
                         h=c['h'], k=c['k'], **support, Closed=closed,
                         Solver_Dependent=closed and not support['Independent_Optimal']))
    if seen != set(by_id):
        raise ValueError('certificate cohort differs from instance cohort')
    return rows


def counts(rows):
    return dict(Instances=len(rows), Theory=sum(r['Theory_Attained'] for r in rows),
                Clique=sum(r['Clique_Attained'] for r in rows),
                Overlap=sum(r['Theory_Attained'] and r['Clique_Attained'] for r in rows),
                Independent=sum(r['Independent_Optimal'] for r in rows),
                SolverDependent=sum(r['Solver_Dependent'] for r in rows),
                Closed=sum(r['Closed'] for r in rows), Open=sum(not r['Closed'] for r in rows))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    args = parser.parse_args()
    certificates = [json.loads(line) for line in (args.report/'certificates.jsonl').read_text().splitlines()]
    with (args.report/'instances.csv').open(newline='') as stream:
        instances = list(csv.DictReader(stream))
    print(json.dumps(counts(classify(certificates, instances)), sort_keys=True))
