"""Validate the two main_r1 experiments and generate the manuscript tables."""

import argparse
from collections import Counter
import csv
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import re
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmarks.families import product_instances
from benchmarks.symmetry_metrics import compare_cnf_sizes
from src.core.graph_utils import cycle_graph
from src.core.io import source_digest
from scripts.summarize_symmetry import read_run, summarize

FAMILY_ORDER = ('C', 'CxC', 'CxP', 'PxP', 'CoC', 'CoP', 'PoC', 'PoP')
LABELS = {'C': r'$C_n$', **{
    f'{a}{op}{b}': f'${a}_n ' + (r'\mathbin{\square}' if op == 'x' else r'\circ') + f' {b}_m$'
    for a in 'CP' for b in 'CP' for op in 'xo'
}}
RULES = {'root=0+order': 'Gốc + thứ tự', 'order': 'Thứ tự', 'none': 'Không thêm'}


def table(output, filename, columns, header, body):
    lines = ['% Generated from main runs; do not edit numbers manually.',
             r'\begin{tabular}{' + columns + '}', r'\toprule', header + r' \\', r'\midrule']
    lines += [' & '.join(map(str, row)) + r' \\' for row in body]
    lines += [r'\bottomrule', r'\end{tabular}', '']
    (output / filename).write_text('\n'.join(lines), encoding='utf-8')


def expected_names(config):
    if config['family'] == 'C':
        return {f'C_{n}' for n in range(config['first'], config['last'] + 1)}
    return {f'{a}_{n}{op}{b}_{m}' for n in range(config['first'], config['last'] + 1)
            for m in range(config['m_first'], config['m_last'] + 1)
            for a, op, b in (('C','x','C'), ('C','x','P'), ('P','x','P'),
                             ('C','o','C'), ('C','o','P'), ('P','o','C'), ('P','o','P'))}


@lru_cache(maxsize=1)
def products(n, m):
    return dict(product_instances(n, m))


def graph_for(name):
    if re.fullmatch(r'C_\d+', name):
        return cycle_graph(int(name.split('_')[1]))
    n, m = map(int, re.findall(r'\d+', name))
    return products(n, m)[name]


def load_experiment(path, family):
    path = Path(path)
    rows = read_run(path)
    metadata = json.loads(path.with_suffix('.metadata.json').read_text())
    config = metadata['config']
    if config['family'] != family or not config.get('comparison'):
        raise ValueError(f'{path}: incorrect experiment family/configuration')
    if {r['Graph'] for r in rows} != expected_names(config):
        raise ValueError(f'{path}: incomplete sweep or unexpected graph identifiers')
    with path.open(newline='') as source:
        if next(csv.reader(source)) != metadata['schema']:
            raise ValueError(f'{path}: header does not match manifest')
    if metadata['source_sha256'] != source_digest():
        raise ValueError(f'{path}: restore the recorded source before validating CNF counts')
    # A restarted unfinished pair can leave an earlier witness: use the latest
    # record for each graph/configuration, then match it to the committed CSV row.
    witnesses = {}
    witness_path = path.with_suffix('.witnesses.jsonl')
    for line in witness_path.read_text().splitlines():
        record = json.loads(line)
        enabled = record['configuration']['symmetry']
        if type(enabled) is not bool:
            raise ValueError('invalid witness configuration')
        witnesses[record['Graph'], enabled] = record['result']
    checked = 0
    for row in rows:
        graph = graph_for(row['Graph'])
        if int(row['V']) != len(graph) or int(row['E']) != graph.number_of_edges():
            raise ValueError(f"graph size mismatch: {row['Graph']}")
        # Recompute both emitted CNFs without invoking a SAT solver.
        counts = compare_cnf_sizes(graph, int(row['Count_Span']))
        for key in ('Symmetry_Rule', 'Var_Base', 'Var_Sym', 'Clause_Base', 'Clause_Sym',
                    'Clause_Raw_Base', 'Clause_Raw_Sym'):
            if str(row[key]) != str(counts[key]):
                raise ValueError(f"CNF count/rule mismatch: {row['Graph']} {key}")
        for suffix, enabled in (('Base', False), ('Sym', True)):
            result = witnesses[row['Graph'], enabled]
            if result['status'] != row[f'Status_{suffix}'] or result['span'] != row[f'lambda_{suffix}']:
                raise ValueError(f"witness status/span mismatch: {row['Graph']}")
            if abs(result['runtime'] - row[f'Time_{suffix}']) > 0.0000006:
                raise ValueError('witness runtime mismatch')
            labels = {int(vertex): label for vertex, label in result['labels']}
            if set(labels) != set(graph) or len(labels) != len(result['labels']):
                raise ValueError('incomplete/duplicate witness vertices')
            if any(type(a) is not int or not 0 <= a <= result['span'] for a in labels.values()):
                raise ValueError('witness label domain violation')
            # Independently traverse all length-one/two walks; do not use the
            # encoder or its distance-pair builder to validate the labeling.
            for u in graph:
                for v in graph[u]:
                    if abs(labels[u] - labels[v]) < 2:
                        raise ValueError('witness adjacency violation')
                    for w in graph[v]:
                        if w != u and labels[u] == labels[w]:
                            raise ValueError('witness distance-two violation')
            lower = result['proven_lower_bound']
            if not 0 <= lower <= result['span'] or (result['status'] == 'OPT' and lower != result['span']):
                raise ValueError('inconsistent witness bound')
            row[f'Lower_{suffix}'] = lower
            if row[f'Stats_Complete_{suffix}'] != str(result['status'] == 'OPT'):
                raise ValueError('invalid statistics completeness flag')
            if int(row[f'Completed_Attempts_{suffix}']) != result['completed_attempts']:
                raise ValueError('attempt count mismatch')
            for key in ('Conflicts', 'Decisions', 'Propagations'):
                value = int(row[f'{key}_{suffix}'])
                if value < 0 or value != result['solver_stats'][key.lower()]:
                    raise ValueError('SAT counter mismatch')
            for key, stored in (('Encoding_Time', 'encoding_time'), ('SAT_Solve_Time', 'sat_solve_time')):
                value = float(row[f'{key}_{suffix}'])
                if not math.isfinite(value) or value < 0 or abs(value - result[stored]) > 0.0000006:
                    raise ValueError('component timing mismatch')
            checked += 1
    provenance = {'csv': str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
                  'files_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in (path, path.with_suffix('.metadata.json'), witness_path)},
                  'manifest': metadata, 'validated_witnesses': checked}
    return rows, metadata, provenance


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cycles', type=Path, default=ROOT / 'results/runs/cycles_main_r1.csv')
    parser.add_argument('--products', type=Path, default=ROOT / 'results/runs/products_main_r1.csv')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'paper/generated')
    args = parser.parse_args()
    cycles, cm, cp = load_experiment(args.cycles, 'C')
    product_rows, pm, pp = load_experiment(args.products, 'products')
    if cm['source_sha256'] != pm['source_sha256'] or cm['packages'] != pm['packages']:
        raise ValueError('runs use different code or package versions')
    for key in ('solver', 'strategy', 'order_offset'):
        if cm['config'][key] != pm['config'][key]:
            raise ValueError(f'run configurations differ in {key}')
    rows = cycles + product_rows
    output = args.output_dir
    output.mkdir(parents=True, exist_ok=True)
    groups = {f: [r for r in rows if r['Family'] == f] for f in FAMILY_ORDER}
    summaries = {r['Family']: r for r in summarize(rows)}
    coverage, timing, encoding, search, components = [], [], [], [], []
    for family, group in groups.items():
        if not group:
            continue
        data = summaries[family]
        paired = [r for r in group if r['Consistent'] == 'YES']
        spans = [r['lambda_Sym'] for r in paired]
        span_text = str(min(spans)) if spans and min(spans) == max(spans) else f'{min(spans)}--{max(spans)}' if spans else '--'
        rule = data['Symmetry_Rules']
        coverage.append([LABELS[family], len(group), len(paired), len(group)-len(paired), span_text, RULES[rule]])
        fmt = lambda value: '--' if value is None else f'{value:.3f}'
        timing.append([LABELS[family], len(paired), fmt(data['Paired_Time_Base']),
                       fmt(data['Paired_Time_Sym']), fmt(data['Median_Paired_Speedup'])])
        if paired:
            median = lambda key: statistics.median(float(r[key]) for r in paired)
            encoding.append([LABELS[family], f'{median("Var_Reduce_Pct"):.2f}',
                             f'{data["Median_Paired_Clause_Reduction_Pct"]:.2f}',
                             int(sum(r['Clause_Sym'] < r['Clause_Base'] for r in paired)),
                             int(sum(r['Clause_Sym'] == r['Clause_Base'] for r in paired)),
                             int(sum(r['Clause_Sym'] > r['Clause_Base'] for r in paired))])
            search.append([LABELS[family], *[sum(int(r[f'{key}_{suffix}']) for r in paired)
                                            for key in ('Conflicts', 'Decisions') for suffix in ('Base', 'Sym')]])
            components.append([LABELS[family], *[f'{median(key+"_"+suffix):.4f}'
                                                for key in ('Encoding_Time', 'SAT_Solve_Time') for suffix in ('Base','Sym')]])
    table(output,'coverage.tex','lrrrrl', r'Họ & Số cặp & OPT/OPT & Chưa tối ưu & Span (OPT) & Đối xứng',coverage)
    table(output,'timing.tex','lrrrr',r'Họ & OPT/OPT & $\sum t_B$ (s) & $\sum t_S$ (s) & Trung vị $t_B/t_S$',timing)
    table(output,'encoding.tex','lrrrrr',r'Họ & Giảm biến (\%) & Giảm clause (\%) & Giảm & Bằng & Tăng',encoding)
    table(output,'search_stats.tex','lrrrr',r'Họ & Xung đột B & Xung đột S & Quyết định B & Quyết định S',search)
    table(output,'components.tex','lrrrr',r'Họ & Dựng CNF B & Dựng CNF S & SAT B & SAT S',components)
    unresolved = [r for r in rows if r['Consistent'] != 'YES']
    def graph_tex(name):
        a,n,op,b,m = re.fullmatch(r'([CP])_(\d+)([xo])([CP])_(\d+)',name).groups()
        return f'${a}_{{{n}}}'+(r'\mathbin{\square}' if op=='x' else r'\circ')+f'{b}_{{{m}}}$'
    table(output,'unresolved.tex','lrrrrr',r'Đồ thị & $L_B$ & $U_B$ & $L_S$ & $U_S$ & Span đếm',
          [[graph_tex(r['Graph']),r['Lower_Base'],r['lambda_Base'],r['Lower_Sym'],r['lambda_Sym'],r['Count_Span']] for r in unresolved])
    configuration = []
    for title, metadata, data in (('Chu trình',cm,cycles),('Product',pm,product_rows)):
        config=metadata['config']
        domain=f"{config['first']}--{config['last']}"
        configuration.append([title, domain, len(data), config['solver'], config['strategy'], f"{config['timeout']:g}"])
    table(output,'run_config.tex','llrllr',r'Tập & Miền $n$ & Số cặp & Solver & Search & Budget (s)',configuration)
    macros={'CycleCount':len(cycles),'ProductCount':len(product_rows),'ComparisonCount':len(rows),
            'PairedOpt':sum(r['Consistent']=='YES' for r in rows),'UnresolvedCount':len(unresolved),
            'WitnessCount':cp['validated_witnesses']+pp['validated_witnesses'],
            'CycleFirst':cm['config']['first'],'CycleLast':cm['config']['last'],
            'ProductFirst':pm['config']['first'],'ProductLast':pm['config']['last'],
            'ProductMFirst':pm['config']['m_first'],'ProductMLast':pm['config']['m_last'],
            'CycleClauseMedian':f"{summaries['C']['Median_Paired_Clause_Reduction_Pct']:.2f}",
            'CycleTimeRatio':f"{summaries['C']['Median_Paired_Speedup']:.3f}"}
    for family in ('CxC','CoC','CoP'):
        data=summaries[family]
        macros[family+'TimeRatio']=f"{data['Median_Paired_Speedup']:.3f}"
        macros[family+'TotalTimeRatio']=f"{data['Paired_Time_Base']/data['Paired_Time_Sym']:.2f}"
    cop=[r for r in product_rows if r['Family']=='CoP' and r['Consistent']=='YES']
    macros['CoronaPathMatches']=sum(r['lambda_Sym']==int(re.findall(r'\d+',r['Graph'])[1])+4 for r in cop)
    macros['CoronaPathCount']=len(cop)
    (output/'counts.tex').write_text('\n'.join(f'\\newcommand{{\\{k}}}{{{v}}}' for k,v in macros.items())+'\n')
    (output/'sources.json').write_text(json.dumps({'experiments':[cp,pp],
        'exporter_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2)+'\n')
    print(f'Validated {len(rows)} pairs and {macros["WitnessCount"]} feasible witnesses; tables in {output}')


if __name__=='__main__':
    main()
