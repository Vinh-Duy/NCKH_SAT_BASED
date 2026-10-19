"""Audit the frozen construction study and export descriptive summaries.

Uses only the standard library. Checks every graph, labeling, lower-bound
certificate, shared partition and complete observation domain. UNKNOWN is
never treated as infeasibility. Summary counts are reconstructed from witnesses.
"""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.verify_clique_certificate import graph_digest, verify as clique_verify
from scripts.matching_bound_certificate import verify as matching_verify
from scripts.construct_color_order import verify_order

DEFAULT = ROOT/'results/analysis/certificate_validation/v1_20261017'
METHODS = ('greedy', 'matching_h', 'random_order', 'insertion_order', 'dsatur_h')
LABELS = dict(greedy='Greedy', matching_h='Matching, spacing $h$',
              random_order='Random order', insertion_order='Insertion order',
              dsatur_h='DSATUR, spacing $h$')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def write_csv(path, rows):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def records(path, key):
    result = {}
    for line in path.read_text().splitlines():
        r = json.loads(line)
        if r[key] in result:
            raise ValueError(f'duplicate {key} in {path}')
        result[r[key]] = r
    return result


def expect(row, key, expected):
    text = '' if expected is None else str(expected)
    if row[key] != text:
        raise ValueError(f'{row.get("Instance", "?")} {row.get("Method", "?")}: incorrect {key}')


def partition(labels, spacing):
    if any(a % spacing for a in labels):
        raise ValueError('labels do not use the claimed class spacing')
    values = sorted(set(labels))
    if values != [spacing*i for i in range(len(values))]:
        raise ValueError('class labels have gaps')
    return [[v for v, a in enumerate(labels) if a == value] for value in values]


def audit(directory):
    prepared = json.loads((directory/'prepared.json').read_text())
    source = json.loads((directory/'sources.json').read_text())
    if source['identity'] != prepared:
        raise ValueError('preparation and completion manifests disagree')
    for name, expected in source['outputs_sha256'].items():
        if digest(directory/name) != expected:
            raise ValueError(f'archived output changed: {name}')
    for name, expected in [('protocol.json', prepared['protocol_sha256']), ('graphs.jsonl', prepared['graphs_sha256'])]:
        if digest(directory/name) != expected:
            raise ValueError(f'prepared input changed: {name}')
    config = json.loads((directory/'protocol.json').read_text())
    graphs = records(directory/'graphs.jsonl', 'instance')
    witnesses = records(directory/'witnesses.jsonl', 'id')
    proofs = records(directory/'matching_certificates.jsonl', 'id')
    checked = {key:clique_verify(c) for key, c in witnesses.items()}
    checked_matching = {key:matching_verify(c) for key, c in proofs.items()}
    expected_keys = {(name,h,k,m) for name in graphs for h,k in config['parameter_pairs'] for m in METHODS}
    rows = read_csv(directory/'observations.csv')
    observed = {}
    for row in rows:
        key = row['Instance'], int(row['h']), int(row['k']), row['Method']
        if key in observed:
            raise ValueError('duplicate observation')
        observed[key] = row
    if set(observed) != expected_keys or len(rows) != config['expected_observations'] or len(graphs) != config['expected_graphs']:
        raise ValueError('observation cohort is incomplete or differs from the protocol')
    prior = ROOT/prepared['historical_graph_source']
    if digest(prior) != prepared['historical_graph_source_sha256']:
        raise ValueError('historical comparison source changed')
    historical_hashes = {json.loads(line)['graph_sha256'] for line in prior.read_text().splitlines()}
    if historical_hashes & {g['sha256'] for g in graphs.values()}:
        raise ValueError('historical labeled graph appears in new cohort')
    if len({g['sha256'] for g in graphs.values()}) != len(graphs):
        raise ValueError('duplicate labeled graph')
    portfolio, used_witnesses, used_proofs = [], set(), set()
    for name, record in graphs.items():
        graph = record['graph']
        n = graph['n']
        if graph_digest(graph) != record['sha256']:
            raise ValueError('cohort graph hash mismatch')
        adjacency = [set() for _ in range(n)]
        for u,v in graph['edges']:
            adjacency[u].add(v)
            adjacency[v].add(u)
        complement = [{v for v in range(n) if v != u and v not in adjacency[u]
                       and not adjacency[u] & adjacency[v]} for u in range(n)]
        eligible = not any(complement[u] & complement[v] for u in range(n) for v in complement[u])
        delta = max(map(len, adjacency), default=0)
        for h,k in config['parameter_pairs']:
            case = {m:observed[name,h,k,m] for m in METHODS}
            greedy_span = checked[case['greedy']['Witness_ID']]['upper_bound']
            reference = witnesses[case['matching_h']['Witness_ID']]
            classes = partition(reference['labels'], h)
            if any(len(cell) > 2 for cell in classes):
                raise ValueError('matching partition contains a class larger than two')
            shared_hash = hashlib.sha256(json.dumps(classes).encode()).hexdigest()
            clique_lb = checked[reference['id']]['lower_bound']
            matching_lb = None
            if eligible:
                matching_lb = checked_matching[reference['id']]['lower_bound']
            degree_lb = h+(delta-1)*k if delta else 0
            lower = max(degree_lb, clique_lb, matching_lb or 0)
            available, certified_methods = {}, []
            for method, row in case.items():
                for field, value in dict(Family=record['family'],V=n,Edges=len(graph['edges']),
                    Graph_SHA256=record['sha256'],Degree_LB=degree_lb,Clique_LB=clique_lb,
                    Matching_LB=matching_lb,Best_LB=lower,Partition_SHA256=shared_hash,
                    Matched_Classes=len(classes)).items():
                    expect(row, field, value)
                span = None
                if row['Status'] == 'FEASIBLE':
                    identifier = f'{name}:h{h}k{k}:{method}'
                    expect(row, 'Witness_ID', identifier)
                    c = witnesses[identifier]
                    if (c['graph'],c['instance'],c['h'],c['k'],c['clique']) != (graph,name,h,k,reference['clique']):
                        raise ValueError('witness does not match observation')
                    used_witnesses.add(identifier)
                    span = checked[identifier]['upper_bound']
                    if eligible:
                        proof = proofs[identifier]
                        if (proof['graph'],proof['h'],proof['k'],proof['labels']) != (graph,h,k,c['labels']):
                            raise ValueError('matching proof and witness disagree')
                        if checked_matching[identifier]['lower_bound'] != matching_lb:
                            raise ValueError('matching bounds disagree')
                        used_proofs.add(identifier)
                    if method in ('random_order', 'insertion_order'):
                        ordered = partition(c['labels'], k)
                        if sorted(ordered) != sorted(classes):
                            raise ValueError('ordering arm changes the partition')
                        order = [classes.index(cell) for cell in ordered]
                        if verify_order(n,graph['edges'],classes,order,h,k)['labels'] != c['labels']:
                            raise ValueError('ordering witness differs from sufficient condition')
                    available[method] = span
                    if span == lower:
                        certified_methods.append(method)
                elif row['Status'] == 'UNKNOWN':
                    if method not in ('random_order', 'insertion_order') or h == k:
                        raise ValueError('invalid UNKNOWN outcome')
                    expect(row, 'Witness_ID', '')
                else:
                    raise ValueError('invalid outcome status')
                if span is not None and span < lower:
                    raise ValueError('witness contradicts lower bound')
                for field, value in dict(Span=span,Gap=None if span is None else span-lower,
                    Certified=span is not None and span == lower,
                    Clique_Certified=span is not None and span == clique_lb,
                    Matching_Certified=span is not None and span == matching_lb,
                    Improves_Greedy=span is not None and span < greedy_span).items():
                    expect(row, field, value)
                attempts = int(row['Attempts'])
                if method in ('random_order','insertion_order') and h > k:
                    if not 1 <= attempts <= config['ordering_attempts']:
                        raise ValueError('invalid attempt count')
                    if span is None and attempts != config['ordering_attempts']:
                        raise ValueError('UNKNOWN before budget exhausted')
                elif attempts != 0:
                    raise ValueError('attempts recorded for a non-search arm')
            best = min(available.values())
            portfolio.append(dict(Instance=name,Family=record['family'],h=h,k=k,Best_LB=lower,
                Best_UB=best,Gap=best-lower,Certified=best==lower,
                Certifying_Methods=';'.join(certified_methods),
                Best_Methods=';'.join(m for m in METHODS if available.get(m)==best),
                Matching_Eligible=eligible,Matching_LB=matching_lb,
                Matching_Strictly_Stronger=matching_lb is not None and matching_lb > max(degree_lb,clique_lb),
                Matching_Necessary=best==lower and best > max(degree_lb,clique_lb)))
    if used_witnesses != set(witnesses) or used_proofs != set(proofs):
        raise ValueError('extra or missing witness/proof')
    totals = {m:dict(observations=sum(r['Method']==m for r in rows),
                    feasible=sum(r['Method']==m and r['Status']=='FEASIBLE' for r in rows),
                    certified=sum(r['Method']==m and r['Certified']=='True' for r in rows),
                    improves_greedy=sum(r['Method']==m and r['Improves_Greedy']=='True' for r in rows)) for m in METHODS}
    if totals != source['totals']:
        raise ValueError('stored totals differ from independently checked rows')
    # Reconstruct the family/parameter summary, including zero-success cells.
    summaries = read_csv(directory/'summary.csv')
    summary_keys = [(r['Family'],r['h'],r['k'],r['Method']) for r in summaries]
    required_summaries = {(r['Family'],r['h'],r['k'],r['Method']) for r in rows}
    if len(summary_keys) != len(set(summary_keys)) or set(summary_keys) != required_summaries:
        raise ValueError('summary domain is incomplete or duplicated')
    for r in summaries:
        subset = [x for x in rows if (x['Family'],x['h'],x['k'],x['Method']) == (r['Family'],r['h'],r['k'],r['Method'])]
        gaps = [int(x['Gap']) for x in subset if x['Gap']]
        values = dict(Cases=len(subset),Feasible=len(gaps),Unknown=len(subset)-len(gaps),
                      Certified=sum(x['Certified']=='True' for x in subset),
                      Improves_Greedy=sum(x['Improves_Greedy']=='True' for x in subset),
                      Median_Gap=statistics.median(gaps) if gaps else None)
        for key,value in values.items():
            expect(r,key,value)
    statistics_out = dict(graphs=len(graphs),instances=len(portfolio),observations=len(rows),
        checked_labelings=len(witnesses),checked_matching_certificates=len(proofs),
        portfolio_certified=sum(p['Certified'] for p in portfolio),
        matching_eligible=sum(p['Matching_Eligible'] for p in portfolio),
        matching_stronger=sum(p['Matching_Strictly_Stronger'] for p in portfolio),
        matching_necessary=sum(p['Matching_Necessary'] for p in portfolio),methods=totals)
    return rows, portfolio, statistics_out


def export(directory):
    rows, portfolio, stats = audit(directory)
    write_csv(directory/'portfolio.csv', portfolio)
    family_rows = []
    for family in sorted({r['Family'] for r in rows}):
        cases = [p for p in portfolio if p['Family']==family]
        family_rows.append(dict(Family=family,Cases=len(cases),
            **{m:sum(r['Family']==family and r['Method']==m and r['Certified']=='True' for r in rows) for m in METHODS},
            Portfolio=sum(p['Certified'] for p in cases),
            Matching_Eligible=sum(p['Matching_Eligible'] for p in cases)))
    write_csv(directory/'family_summary.csv', family_rows)
    method_lines = [r'\begin{tabular}{lrrrr}',r'\toprule',
                    r'Method & Feasible & Unknown & Certified & Improved\\\midrule']
    for method in METHODS:
        r = stats['methods'][method]
        method_lines.append(f'{LABELS[method]} & {r["feasible"]} & {r["observations"]-r["feasible"]} & {r["certified"]} & {r["improves_greedy"]}'+r'\\')
    method_lines += [r'\bottomrule',r'\end{tabular}']
    (directory/'methods.tex').write_text('\n'.join(method_lines)+'\n')
    family_lines = [r'\begin{tabular}{lrrrrr}',r'\toprule',
                    r'Family & Cases & Greedy & Insertion & DSATUR & Union\\\midrule']
    for r in family_rows:
        family_lines.append(f'{r["Family"]} & {r["Cases"]} & {r["greedy"]} & {r["insertion_order"]} & {r["dsatur_h"]} & {r["Portfolio"]}'+r'\\')
    family_lines += [r'\bottomrule',r'\end{tabular}']
    (directory/'families.tex').write_text('\n'.join(family_lines)+'\n')
    stats['audit_sources_sha256'] = {p:digest(ROOT/p) for p in (
        'scripts/audit_certificate_validation.py','scripts/verify_clique_certificate.py',
        'scripts/matching_bound_certificate.py','scripts/construct_color_order.py')}
    stats['completion_manifest_sha256'] = digest(directory/'sources.json')
    (directory/'audit.json').write_text(json.dumps(stats,sort_keys=True,indent=2)+'\n')
    return stats


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, default=DEFAULT)
    args = parser.parse_args()
    print(json.dumps(export(args.input), indent=2))
