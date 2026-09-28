"""Audit the fixed pilot and compare saved witnesses with proved reference bounds.

Never modifies benchmark CSV/statuses or treats solver agreement as an UNSAT proof.
"""
import argparse
import ast
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import networkx as nx
from benchmarks.general_suite import SUITE_NAME, general_pilot


def reference_bounds(name, graph, h, k):
    """Elementary bounds plus proved equal-gap trees and L(2,1) grids.

    Names are used only for grids regenerated and checked by the caller.
    These references are comparisons, never injected into recorded solver bounds.
    """
    n = len(graph)
    delta = max(dict(graph.degree()).values(), default=0)
    degree = h + (delta-1)*min(h, k) if delta else 0
    upper = max(0, n-1)*max(h, k)
    exact, rule = None, "degree / distinct spaced labels"
    if n and nx.is_tree(graph) and h == k:
        exact, rule = h*delta, "equal-gap tree: h*Delta"
    elif name.startswith('P_') and 'xP_' in name and (h, k) == (2, 1):
        a, b = (int(x) for x in name[2:].split('xP_'))
        upper = min(upper, 6)
        if a >= 4 and b >= 4:
            exact, rule = 6, "grid L(2,1), both dimensions >=4"
    return dict(Degree_LB=degree, Theory_LB=exact if exact is not None else degree,
                Theory_UB=exact if exact is not None else upper,
                Exact_Reference=exact, Reference=rule)


def check_observation(row, record, graph, family, config):
    """Check a saved witness using shortest paths, independently of the encoder."""
    name, method = row['Instance'], row['Method']
    h, k = int(row['h']), int(row['k'])
    cfg, result = record['configuration'], record['result']
    if (record['Graph'] != row['Graph'] or row['Family'] != family
            or (cfg['h'], cfg['k'], cfg['method']) != (h, k, method)
            or (result['h'], result['k']) != (h, k)):
        raise ValueError('configuration mismatch')
    if (len(cfg['vertices']) != len(graph) or set(cfg['vertices']) != set(graph)
            or len(cfg['edges']) != graph.number_of_edges()
            or {frozenset(e) for e in cfg['edges']} != {frozenset(e) for e in graph.edges()}):
        raise ValueError('saved graph mismatch')
    delta = max(dict(graph.degree()).values(), default=0)
    if (int(row['V']), int(row['E']), int(row['Delta'])) != (len(graph), graph.number_of_edges(), delta):
        raise ValueError('graph statistics mismatch')
    if family == 'tree' and int(row['Diameter']) != nx.diameter(graph):
        raise ValueError('diameter mismatch')
    if row['Status'] not in {'OPT', 'FEASIBLE'} or result['status'] != row['Status']:
        raise ValueError('this audit requires a saved feasible witness for each observation')
    span, lower = int(row['Span']), int(row['LB'])
    if (span != result['span'] or lower != result['proven_lower_bound'] or not 0 <= lower <= span
            or row['Status'] == 'OPT' and lower != span):
        raise ValueError('recorded bounds/status mismatch')
    labels = {ast.literal_eval(v): a for v, a in result['labels']}
    if len(result['labels']) != len(graph) or set(labels) != set(graph):
        raise ValueError('missing or duplicate labels')
    if any(type(a) is not int or not 0 <= a <= span for a in labels.values()):
        raise ValueError('invalid label domain')
    for u in graph:
        for v, d in nx.single_source_shortest_path_length(graph, u, cutoff=2).items():
            if d and abs(labels[u]-labels[v]) < (h if d == 1 else k):
                raise ValueError('invalid witness')
    witness_span = max(labels.values(), default=0)-min(labels.values(), default=0)
    if lower > witness_span or row['Status'] == 'OPT' and witness_span != span:
        raise ValueError('recorded lower bound contradicts witness span')
    wall, limit = float(row['Wall_Time']), float(row['Limit'])
    if (not math.isfinite(wall) or wall <= 0 or limit != config['timeout']
            or not math.isclose(wall, result['wall_time'], rel_tol=1e-12)
            or row['Termination'] != result['termination']
            or row['Termination'] not in {'RETURNED', 'WALL_TIMEOUT'}):
        raise ValueError('runtime/termination mismatch')
    ref = reference_bounds(name, graph, h, k)
    exact = ref['Exact_Reference']
    if witness_span < ref['Theory_LB'] or lower > ref['Theory_UB']:
        raise ValueError('witness or solver bound contradicts theory')
    if row['Status'] == 'OPT' and (span > ref['Theory_UB'] or exact is not None and span != exact):
        raise ValueError('solver optimum contradicts exact reference')
    return dict(Graph=row['Graph'], Instance=name, Family=family, h=h, k=k,
                Method=method, Repeat=int(row['Repeat']), V=len(graph), E=graph.number_of_edges(),
                Status=row['Status'], Recorded_LB=lower, Span=span, Witness_Span=witness_span,
                **ref, Excess_Over_Theory_LB=witness_span-ref['Theory_LB'],
                Theory_Optimal=witness_span == ref['Theory_LB'],
                Reference_Check='NA' if exact is None else 'MATCH' if witness_span == exact else 'ABOVE_EXACT',
                Wall_Time=wall, Within_Budget=wall <= limit)


def check_pairs(observations):
    groups = {}
    for row in observations:
        groups.setdefault((row['Instance'], row['h'], row['k'], row['Repeat']), []).append(row)
    for pair in groups.values():
        optima = {r['Span'] for r in pair if r['Status'] == 'OPT'}
        if len(optima) > 1:
            raise ValueError('inconsistent solver optima')
        if max(r['Recorded_LB'] for r in pair) > min(r['Witness_Span'] for r in pair):
            raise ValueError('cross-solver bounds contradict witnesses')
    return groups


def audit(path):
    path = Path(path)
    meta = json.loads(path.with_suffix('.metadata.json').read_text())
    config = meta['config']
    if (config['suite'] != SUITE_NAME or config['pairs'] != [[1,1],[2,1],[3,2]]
            or set(config['methods']) != {'cadical','gurobi'} or config['repeats'] != 1
            or config['timeout'] != 30 or config['symmetry'] or config['ilp_threads'] != 1):
        raise ValueError('expected the declared 234-observation pilot protocol')
    if meta['packages']['networkx'] != nx.__version__:
        raise ValueError('regenerate with the recorded NetworkX version')
    cohort = {name:(family,graph) for name,family,graph in general_pilot()}
    expected = {f'{name}__h{h}_k{k}__r0__{method}'
                for name in cohort for h,k in config['pairs'] for method in config['methods']}
    with path.open(newline='') as f:
        rows = list(csv.DictReader(f))
    records = [json.loads(line) for line in path.with_suffix('.witnesses.jsonl').read_text().splitlines()]
    witnesses = {r['Graph']:r for r in records}
    if (len(rows) != len(expected) or {r['Graph'] for r in rows} != expected
            or len(records) != len(expected) or set(witnesses) != expected):
        raise ValueError('missing, duplicate or unexpected observations')
    checked = []
    for row in rows:
        if row['Graph'] != f"{row['Instance']}__h{row['h']}_k{row['k']}__r{row['Repeat']}__{row['Method']}":
            raise ValueError('identity mismatch')
        family, graph = cohort[row['Instance']]
        checked.append(check_observation(row, witnesses[row['Graph']], graph, family, config))
    groups = check_pairs(checked)
    summaries = []
    for family,h,k in sorted({(r['Family'],r['h'],r['k']) for r in checked}):
        selected = [r for r in checked if (r['Family'],r['h'],r['k']) == (family,h,k)]
        selected_pairs = [pair for pair in groups.values() if (pair[0]['Family'],pair[0]['h'],pair[0]['k']) == (family,h,k)]
        jointly = [pair for pair in selected_pairs if all(r['Status']=='OPT' and r['Within_Budget'] for r in pair)]
        summary = dict(Family=family,h=h,k=k,Cases=len(selected_pairs),Joint_OPT_Within_Budget=len(jointly),
                       Exact_Reference_Cases=sum(pair[0]['Exact_Reference'] is not None for pair in selected_pairs))
        for method in config['methods']:
            subset = [r for r in selected if r['Method']==method]
            summary.update({method+'_OPT':sum(r['Status']=='OPT' for r in subset),
                            method+'_FEASIBLE':sum(r['Status']=='FEASIBLE' for r in subset),
                            method+'_Theory_Optimal':sum(r['Theory_Optimal'] for r in subset),
                            method+'_Paired_Median_Seconds':statistics.median(r['Wall_Time'] for pair in jointly for r in pair if r['Method']==method) if jointly else None})
        summaries.append(summary)
    return checked, summaries, meta


def export(path, output):
    path, output = Path(path), Path(output)
    checked, summaries, meta = audit(path)
    output.mkdir(parents=True, exist_ok=False)
    for name, rows in [('observations.csv', checked), ('summary.csv', summaries)]:
        with (output/name).open('w', newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    hashes = {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in
              (path,path.with_suffix('.metadata.json'),path.with_suffix('.witnesses.jsonl'),
               Path(__file__),ROOT/'benchmarks/general_suite.py')}
    manifest = dict(files_sha256=hashes,original_manifest=meta,observations=len(checked),
                    scope='Regenerated graphs, independent shortest-path witness validation, reference bounds and paired consistency; no UNSAT proof, timer reconstruction or CNF recount.')
    (output/'sources.json').write_text(json.dumps(manifest,indent=2)+'\n')
    lines=[r'\begin{tabular}{llrrrr}',r'\toprule',
           r'Họ & $(h,k)$ & Mẫu & SAT OPT & ILP OPT & Có công thức\\',r'\midrule']
    for r in summaries:
        lines.append(f"{r['Family']} & $({r['h']},{r['k']})$ & {r['Cases']} & {r['cadical_OPT']} & {r['gurobi_OPT']} & {r['Exact_Reference_Cases']}"+r'\\')
    lines.extend([r'\bottomrule',r'\end{tabular}'])
    (output/'summary.tex').write_text('\n'.join(lines)+'\n')
    return checked, summaries


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=ROOT/'results/runs/general_pilot_v1.csv')
    parser.add_argument('--output-dir',type=Path,default=ROOT/'results/analysis/general_pilot_v1')
    parser.add_argument('--check-only',action='store_true',help='validate inputs without writing or replacing analysis files')
    args=parser.parse_args()
    if args.check_only:
        checked, summary, _=audit(args.input)
        print(f'Validated {len(checked)} observations; no files written')
    else:
        checked, summary=export(args.input,args.output_dir)
        print(f'Validated {len(checked)} observations; wrote {len(summary)} groups to {args.output_dir}')
