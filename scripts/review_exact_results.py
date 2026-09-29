"""Review current exact experiments and count models at a shared label bound.

No solver calls, historical count reconstruction, or changes to raw results.
Other CSVs are inventoried only, never silently promoted to validated evidence.
"""
import argparse
import ast
from collections import Counter
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
from benchmarks.benchmark_sat_vs_ilp import instances
from benchmarks.general_suite import general_pilot
from scripts.audit_general_pilot import audit, check_observation, check_pairs
from scripts.export_paper_tables import expected_names, graph_for
from src.core.graph_utils import graph_constraints
from src.models.ilp_assignment import make_spec
from src.models.sat_encoding import build_cnf


def read_csv(path):
    with Path(path).open(newline='') as stream:
        return list(csv.DictReader(stream))


def validate_saved_labels(graph, encoded, span, h, k):
    labels = {ast.literal_eval(v): a for v, a in encoded}
    if len(encoded) != len(graph) or set(labels) != set(graph):
        raise ValueError('incomplete or duplicate witness')
    if type(span) is not int or span < 0 or any(type(a) is not int or not 0 <= a <= span for a in labels.values()):
        raise ValueError('invalid label domain')
    for u in graph:
        for v, distance in nx.single_source_shortest_path_length(graph, u, cutoff=2).items():
            if distance and abs(labels[u]-labels[v]) < (h if distance == 1 else k):
                raise ValueError('invalid witness')
    return max(labels.values(), default=0)-min(labels.values(), default=0)


def audit_symmetry(path):
    """Witness/status audit only: does NOT bypass the old CNF source-hash gate."""
    rows = read_csv(path)
    meta = json.loads(path.with_suffix('.metadata.json').read_text())
    if len(rows) != len(expected_names(meta['config'])) or {r['Graph'] for r in rows} != expected_names(meta['config']):
        raise ValueError('incomplete symmetry sweep')
    if list(rows[0]) != meta['schema']:
        raise ValueError('schema mismatch')
    records = {}
    for line in path.with_suffix('.witnesses.jsonl').read_text().splitlines():
        record = json.loads(line)
        flag = record['configuration']['symmetry']
        if type(flag) is not bool:
            raise ValueError('invalid symmetry flag')
        records[record['Graph'], flag] = record['result']  # latest completed record
    if set(records) != {(r['Graph'], flag) for r in rows for flag in (False, True)}:
        raise ValueError('witness identities mismatch')
    statuses = Counter()
    for row in rows:
        graph = graph_for(row['Graph'])
        if (int(row['V']), int(row['E'])) != (len(graph), graph.number_of_edges()):
            raise ValueError('graph size mismatch')
        pair = []
        for suffix, flag in [('Base', False), ('Sym', True)]:
            result = records[row['Graph'], flag]
            status, span = result['status'], result['span']
            if status not in {'OPT', 'FEASIBLE'} or status != row['Status_'+suffix] or span != int(row['lambda_'+suffix]):
                raise ValueError('status/span mismatch')
            runtime = float(row['Time_'+suffix])
            if not math.isfinite(runtime) or runtime < 0 or abs(runtime-result['runtime']) > 6e-7:
                raise ValueError('runtime mismatch')
            actual = validate_saved_labels(graph, result['labels'], span, 2, 1)
            lower = result['proven_lower_bound']
            if not 0 <= lower <= actual <= span or status == 'OPT' and not lower == actual == span:
                raise ValueError('bounds contradict witness')
            pair.append(dict(Span=span, Recorded_LB=lower, Witness_Span=actual, Status=status,
                             Instance=row['Graph'], h=2, k=1, Repeat=0))
            statuses[status] += 1
        check_pairs(pair)
    return dict(Run=path.stem, Rows=len(rows), Witnesses=2*len(rows), OPT=statuses['OPT'],
                FEASIBLE=statuses['FEASIBLE'], Scope='witness/status/paired bounds; historical CNF counts and times not reproduced')


def audit_trees(path):
    meta = json.loads(path.with_suffix('.metadata.json').read_text())
    cfg = meta['config']
    if cfg['families'] != ['tree'] or cfg['pairs'] != [[3,2]] or set(cfg['methods']) != {'cadical','gurobi'}:
        raise ValueError('unexpected tree protocol')
    if meta['packages']['networkx'] != nx.__version__:
        raise ValueError('NetworkX version differs')
    graphs = {name: (family, graph) for name, family, graph in instances(
        cfg['families'], cfg['min_vertices'], cfg['max_vertices'], cfg['seed'],
        cfg.get('tree_sizes'), cfg.get('seeds'))}
    expected = {f'{name}__h3_k2__r{r}__{method}' for name in graphs
                for r in range(cfg['repeats']) for method in cfg['methods']}
    rows = read_csv(path)
    saved = [json.loads(line) for line in path.with_suffix('.witnesses.jsonl').read_text().splitlines()]
    records = {r['Graph']: r for r in saved}
    if len(rows) != len(expected) or {r['Graph'] for r in rows} != expected or len(saved) != len(expected) or set(records) != expected:
        raise ValueError('incomplete tree observations')
    checked = []
    for row in rows:
        if row['Graph'] != f"{row['Instance']}__h{row['h']}_k{row['k']}__r{row['Repeat']}__{row['Method']}":
            raise ValueError('identity mismatch')
        family, graph = graphs[row['Instance']]
        # Earlier paired-run schemas did not store Delta/Diameter. Derive them
        # from the regenerated graph for the checker, never rewrite the CSV.
        augmented = dict(row)
        augmented.setdefault('Delta', max(dict(graph.degree()).values(), default=0))
        augmented.setdefault('Diameter', nx.diameter(graph))
        checked.append(check_observation(augmented, records[row['Graph']], graph, family, cfg))
    check_pairs(checked)
    optima = {}
    for row in checked:
        if row['Status'] == 'OPT':
            key = row['Instance']
            if key in optima and optima[key] != row['Span']:
                raise ValueError('repeat optima disagree')
            optima[key] = row['Span']
    return dict(Run=path.stem, Rows=len(rows), Witnesses=len(checked),
                OPT=sum(r['Status']=='OPT' for r in checked), FEASIBLE=sum(r['Status']=='FEASIBLE' for r in checked),
                Scope='regenerated trees/independent BFS/witness/status/repeat consistency; no UNSAT certificate')


def count_models(graph, span, h, k):
    graph = nx.convert_node_labels_to_integers(graph)
    edges, pairs = graph_constraints(graph)
    cnf, variables = build_cnf(len(graph), edges, pairs, span, h, k, simplify=False)
    spec = make_spec(list(graph), edges, pairs, span, h, k)
    forbidden = len(edges)*spec.forbidden_pair_count(h)+len(pairs)*spec.forbidden_pair_count(k)
    predicted = len(graph)*max(span-1,0)+forbidden
    if variables.raw_clause_count != predicted or variables.variable_count != len(graph)*span:
        raise ValueError('SAT count differs from formula')
    # Count raw emissions, including an empty clause for an infeasible bound.
    return dict(V=len(graph), E=len(edges), D2=len(pairs), Model_Span=span,
                SAT_Variables=variables.variable_count, SAT_Raw_Clauses=variables.raw_clause_count,
                ILP_Binary=spec.assignment_variable_count, ILP_Integer=1,
                ILP_Constraints=spec.constraint_count)


def write_csv(path, rows):
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def review(output):
    if output.exists():
        raise ValueError('output must be new; existing reviews are immutable')
    checked, _, _ = audit(ROOT/'results/runs/general_pilot_v1.csv')
    summaries = [dict(Run='general_pilot_v1', Rows=len(checked), Witnesses=len(checked),
                      OPT=sum(r['Status']=='OPT' for r in checked), FEASIBLE=sum(r['Status']=='FEASIBLE' for r in checked),
                      Scope='fixed cohort/independent BFS/witness/reference bounds; no UNSAT certificate')]
    for name in ('tree_l32_compare_r1', 'tree_l32_screen_v2'):
        summaries.append(audit_trees(ROOT/f'results/runs/{name}.csv'))
    for name in ('cycles_main_r1', 'products_main_r1'):
        summaries.append(audit_symmetry(ROOT/f'results/runs/{name}.csv'))
    models = []
    graphs = {name: graph for name, _, graph in general_pilot()}
    for (name,h,k,r), pair in check_pairs(checked).items():
        # Post-hoc common feasible domain, not a reproduction of historical models.
        span = min(row['Witness_Span'] for row in pair)
        models.append(dict(Instance=name, Family=pair[0]['Family'], h=h, k=k,
                           Bound_Source='minimum_validated_witness_span', **count_models(graphs[name],span,h,k)))
    inventory = []
    reviewed = {r['Run'] for r in summaries}
    for p in sorted((ROOT/'results').rglob('*.csv')):
        rows = read_csv(p)
        inventory.append(dict(File=str(p.relative_to(ROOT)), Rows=len(rows), SHA256=hashlib.sha256(p.read_bytes()).hexdigest(),
                              Review='current_witness_audit' if p.parent==ROOT/'results/runs' and p.stem in reviewed else 'inventory_only'))
    output.mkdir(parents=True)
    for name, rows in [('current_runs.csv',summaries),('common_bound_models.csv',models),('csv_inventory.csv',inventory)]:
        write_csv(output/name, rows)
    lines=[r'\begin{tabular}{llrrrrr}',r'\toprule',r'Family & $(h,k)$ & Cases & SAT vars & SAT clauses & ILP binaries & ILP rows\\',r'\midrule']
    for family,h,k in sorted({(r['Family'],r['h'],r['k']) for r in models}):
        group=[r for r in models if (r['Family'],r['h'],r['k'])==(family,h,k)]
        values=[f'{statistics.median(r[key] for r in group):g}' for key in ('SAT_Variables','SAT_Raw_Clauses','ILP_Binary','ILP_Constraints')]
        lines.append(' & '.join([family,f'$({h},{k})$',str(len(group)),*values])+r'\\')
    (output/'models.tex').write_text('\n'.join([*lines,r'\bottomrule',r'\end{tabular}'])+'\n')
    inputs=[ROOT/f'results/runs/{r["Run"]}{suffix}' for r in summaries
            for suffix in ('.csv','.metadata.json','.witnesses.jsonl')]
    sources=[Path(__file__).resolve(), ROOT/'scripts/audit_general_pilot.py',ROOT/'scripts/export_paper_tables.py',
             ROOT/'benchmarks/benchmark_sat_vs_ilp.py',ROOT/'benchmarks/general_suite.py',ROOT/'benchmarks/families.py',
             ROOT/'src/core/graph_utils.py',ROOT/'src/models/sat_encoding.py',ROOT/'src/models/ilp_assignment.py',ROOT/'src/core/parameters.py']
    (output/'sources.json').write_text(json.dumps(dict(
        inputs_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
        review_sources_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        networkx=nx.__version__, total_current_witnesses=sum(r['Witnesses'] for r in summaries),
        scope='Current witnesses checked; other CSVs inventoried only. Common-bound counts are new raw model measurements, not solver runtime or historical CNF recounts.'),indent=2)+'\n')
    print(json.dumps(summaries,indent=2))
    print(f'Wrote {len(models)} common-bound counts; inventoried {len(inventory)} pre-existing CSV files')


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,default=ROOT/'results/analysis/exact_review_20260928')
    review(parser.parse_args().output_dir)
