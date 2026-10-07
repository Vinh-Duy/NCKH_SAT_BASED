"""Audit a completed v2 confirmation and compare retained SAT/Gurobi bounds.

Uses the existing independent witness/theory audit, then validates the progress
ledger. No solver calls, historical data rewriting, or automatic paper updates.
"""
import argparse
import ast
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from benchmarks.benchmark_sat_vs_ilp import PROTOCOL
from benchmarks.general_suite import general_pilot
from scripts.build_confirmation_report import audit, digest, write_csv, verify_cache
from scripts.compare_unresolved_bounds import pair_rows, summarize
from src.core.graph_utils import greedy_labeling, lower_bound


def check_trace(row, result, graph):
    """Validate provenance consistency; lower bounds are trusted solver claims."""
    trace = result.get('progress_trace', [])
    if not trace or trace[0]['event'] != 'incumbent':
        raise ValueError('missing initial progress snapshot')
    h, k = int(row['h']), int(row['k'])
    upper, labels = greedy_labeling(graph, h, k)
    low = lower_bound(graph, h, k)
    first = trace[0]
    if (first['span'], first['lb'], first['source'], first['lower_bound_source']) != (upper, low, 'greedy', 'elementary'):
        raise ValueError('initial progress differs from shared fallback')
    expected_sources = {'greedy', 'sat'} if row['Method'] == 'cadical' else {'greedy', 'gurobi_incumbent'}
    expected_bounds = {'elementary', 'sat_unsat'} if row['Method'] == 'cadical' else {'elementary', 'gurobi_dual', 'gurobi_optimal'}
    previous_time = 0
    done = False
    for point in trace:
        timestamp = point['received_seconds']
        if not math.isfinite(timestamp) or not previous_time <= timestamp <= float(row['Limit']):
            raise ValueError('progress outside the deadline or out of order')
        previous_time = timestamp
        if (point is not first and point['event'] not in {'progress', 'done'}) or done:
            raise ValueError('invalid progress event order')
        done = point['event'] == 'done'
        lb, ub = point['lb'], point['span']
        if type(lb) is not int or type(ub) is not int or not low <= lb <= ub <= upper:
            raise ValueError('progress interval regressed or is invalid')
        if point['status'] not in {'OPT', 'FEASIBLE'} or point['status'] == 'OPT' and lb != ub:
            raise ValueError('invalid progress optimality claim')
        if point['source'] not in expected_sources or point['lower_bound_source'] not in expected_bounds:
            raise ValueError('invalid bound provenance')
        if (point['source'] == 'greedy' and ub != first['span']
                or point['lower_bound_source'] == 'elementary' and lb != first['lb']):
            raise ValueError('initial bound source cannot claim a solver improvement')
        low, upper = lb, ub
    if done != (row['Termination'] == 'RETURNED'):
        raise ValueError('termination disagrees with progress ledger')
    last = trace[-1]
    for key, trace_key in [('span','span'), ('proven_lower_bound','lb'), ('status','status'),
                           ('source','source'), ('lower_bound_source','lower_bound_source')]:
        if result[key] != last[trace_key]:
            raise ValueError('result differs from last received progress')
    if row['Incumbent_Source'] != result['source'] or row['LB_Source'] != result['lower_bound_source']:
        raise ValueError('CSV provenance mismatch')
    updates = [p for p in trace if p['event'] == 'progress']
    if int(row['Progress_Updates']) != len(updates) or result['progress_updates'] != len(updates):
        raise ValueError('progress count mismatch')
    expected_last = updates[-1]['received_seconds'] if updates else None
    saved_last = float(row['Last_Progress_Seconds']) if row['Last_Progress_Seconds'] else None
    if saved_last != expected_last or result['last_progress_seconds'] != expected_last:
        raise ValueError('last progress timestamp mismatch')
    if last['received_seconds'] > result['wall_time']:
        raise ValueError('progress timestamp exceeds total wall time')
    if result['source'] == 'greedy' and {ast.literal_eval(v):a for v,a in result['labels']} != labels:
        raise ValueError('greedy provenance disagrees with the saved labeling')
    initial_only = (row['Termination'] == 'WALL_TIMEOUT' and result['source'] == 'greedy'
                    and result['lower_bound_source'] == 'elementary')
    return dict(Incumbent_Source=result['source'], LB_Source=result['lower_bound_source'],
                Progress_Updates=len(updates), Initial_Fallback=initial_only,
                Initial_LB=first['lb'], Initial_UB=first['span'],
                LB_Improvement=last['lb']-first['lb'], UB_Improvement=first['span']-last['span'])


def collect(path):
    metadata = json.loads(path.with_suffix('.metadata.json').read_text())
    if metadata['config'].get('protocol') != PROTOCOL:
        raise ValueError('this audit requires isolated-progress-v2; do not relabel old metadata')
    checked, instances, coverage, metadata = audit(path)
    with path.open(newline='') as stream:
        rows = {r['Graph']:r for r in csv.DictReader(stream)}
    records = {r['Graph']:r['result'] for r in map(json.loads, path.with_suffix('.witnesses.jsonl').read_text().splitlines())}
    graphs = {name:graph for name,_,graph in general_pilot()}
    # Scope is defined from this run's saved solver evidence, without pooling
    # earlier experiments or theoretical bounds into timed solver intervals.
    open_keys = {(r['Instance'],r['h'],r['k']) for r in instances if r['Combined_LB'] < r['Best_Witness_Span']}
    for row in checked:
        raw, result = rows[row['Graph']], records[row['Graph']]
        row.update(check_trace(raw, result, graphs[row['Instance']]))
        row.update(Termination=raw['Termination'], Open_Instance=(row['Instance'],row['h'],row['k']) in open_keys)
    pairs = pair_rows(checked)
    return checked, instances, coverage, pairs, summarize(pairs)


def export(path, output_root):
    path = Path(path).resolve()
    checked, instances, coverage, pairs, summary = collect(path)
    inputs = [path, path.with_suffix('.metadata.json'), path.with_suffix('.witnesses.jsonl')]
    sources = [Path(__file__).resolve(), ROOT/'scripts/build_confirmation_report.py',
               ROOT/'scripts/audit_general_pilot.py', ROOT/'scripts/compare_unresolved_bounds.py',
               ROOT/'benchmarks/general_suite.py', ROOT/'src/core/graph_utils.py', ROOT/'src/core/parameters.py']
    identity = dict(protocol=PROTOCOL,
                    inputs={str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p):digest(p) for p in inputs},
                    analysis_sources={str(p.relative_to(ROOT)):digest(p) for p in sources})
    version = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16]
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    output = output_root/version
    if output.exists():
        verify_cache(output, identity)
        return output
    temporary = Path(tempfile.mkdtemp(prefix='.building-', dir=output_root))
    try:
        for name, data in [('observations', checked), ('instances', instances), ('coverage', coverage),
                           ('paired_bounds', pairs), ('summary', summary)]:
            write_csv(temporary/f'{name}.csv', data)
        (temporary/'README.md').write_text(f'''# Progress-capture confirmation

Input: `{path.name}`. Protocol: `{PROTOCOL}`.

- {len(checked)} observations; {len(instances)} graph/parameter instances.
- `observations.csv`: independently validated witnesses, reference bounds, and progress provenance.
  `LB_Improvement = saved LB - initial LB`; `UB_Improvement = initial UB - saved UB`.
- `paired_bounds.csv`: one row per graph, parameter pair, and repeat; larger LB is better,
  smaller UB is better. Delta columns are SAT minus ILP. Do not average across different graphs.
- `summary.csv`: ALL pairs and OPEN instances whose intervals remain non-singleton after
  pooling this run's solver bounds across repetitions/backends. This is not the old 21-case subset.
  `Initial_Fallback` means an external timeout retains both shared initial bound sources;
  equality alone is not interpreted as equivalent native solver progress.
- `instances.csv` and `coverage.csv`: coverage and paired timing; timing eligibility uses total
  wall time including cleanup, as in the archived confirmation. Min/max are not confidence intervals.
- `sources.json`: immutable input, analysis-source, and output fingerprints.

SAT progress is observed only at completed span decisions; Gurobi uses validated MIPSOL
labelings and conservative integer dual bounds. Timestamps refer to parent receipt, not
native discovery. Messages received after the deadline are excluded. Callback, transport,
validation, startup and cleanup add measurement overhead. The v1 and v2 timings must not
be pooled. Labels prove feasibility; this audit does not independently verify UNSAT proofs
or Gurobi dual certificates. Report evidence within this cohort and budget, not general equivalence.

The manuscript is not overwritten automatically. Review these outputs before inserting new results.
''')
        (temporary/'sources.json').write_text(json.dumps(dict(identity=identity,
            counts=dict(observations=len(checked), instances=len(instances)),
            outputs_sha256={p.name:digest(p) for p in temporary.iterdir()}), indent=2)+'\n')
        temporary.rename(output)
    except BaseException:
        shutil.rmtree(temporary)
        raise
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output-root', type=Path, default=ROOT/'results/analysis/progress_confirmation')
    args = parser.parse_args()
    print(export(args.input, args.output_root))
