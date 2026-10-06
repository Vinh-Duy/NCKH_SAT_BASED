"""Compare recorded SAT/ILP bounds and audit initial-fallback provenance.

This report is specific to the archived initial/final-message runner. It must
not be used to infer native solver progress at an external timeout.
"""
import ast
from collections import defaultdict
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

from benchmarks.general_suite import general_pilot
from scripts.analyze_confirmation_gaps import analyze
from scripts.build_confirmation_report import audit, digest, group_name, verify_cache, write_csv
from src.core.graph_utils import greedy_labeling, lower_bound
from src.core.io import source_digest


def initial_fallback(row, result, initial):
    """Only call after verifying the archived runner's source fingerprint."""
    upper, labels, lower = initial
    saved = {ast.literal_eval(v): a for v, a in result['labels']}
    equal = (result['span'] == upper and result['proven_lower_bound'] == lower and saved == labels)
    if row['Termination'] == 'WALL_TIMEOUT':
        if row['Status'] != 'FEASIBLE' or not equal:
            raise ValueError('timeout record is inconsistent with the initial-only capture protocol')
        return True
    return False  # Returned OPT can also equal the greedy labeling.


def pair_rows(observations):
    groups = defaultdict(dict)
    for row in observations:
        key = (row['Instance'], row['h'], row['k'], row['Repeat'])
        if row['Method'] in groups[key]:
            raise ValueError('duplicate backend in pair')
        groups[key][row['Method']] = row
    pairs = []
    for (name, h, k, repeat), group in sorted(groups.items()):
        if set(group) != {'cadical', 'gurobi'}:
            raise ValueError('missing backend in pair')
        sat, ilp = group['cadical'], group['gurobi']
        if sat['Open_Instance'] != ilp['Open_Instance']:
            raise ValueError('inconsistent cohort membership')
        row = dict(Instance=name, Group=group_name(sat), h=h, k=k, Repeat=repeat,
                   Open_Instance=sat['Open_Instance'])
        for method, source in [('SAT', sat), ('ILP', ilp)]:
            row.update({method+'_LB': source['Recorded_LB'], method+'_UB': source['Witness_Span'],
                        method+'_Status': source['Status'], method+'_Termination': source['Termination'],
                        method+'_Initial_Fallback': source['Initial_Fallback']})
        row['Delta_LB_SAT_minus_ILP'] = row['SAT_LB']-row['ILP_LB']
        row['Delta_UB_SAT_minus_ILP'] = row['SAT_UB']-row['ILP_UB']
        pairs.append(row)
    return pairs


def summarize(pairs):
    summaries = []
    for scope, selected in [('ALL', pairs), ('OPEN', [p for p in pairs if p['Open_Instance']])]:
        summaries.append(dict(
            Scope=scope, Instances=len({(p['Instance'], p['h'], p['k']) for p in selected}),
            Repeat_Pairs=len(selected),
            SAT_Tighter_LB=sum(p['Delta_LB_SAT_minus_ILP'] > 0 for p in selected),
            Equal_LB=sum(p['Delta_LB_SAT_minus_ILP'] == 0 for p in selected),
            ILP_Tighter_LB=sum(p['Delta_LB_SAT_minus_ILP'] < 0 for p in selected),
            SAT_Better_UB=sum(p['Delta_UB_SAT_minus_ILP'] < 0 for p in selected),
            Equal_UB=sum(p['Delta_UB_SAT_minus_ILP'] == 0 for p in selected),
            ILP_Better_UB=sum(p['Delta_UB_SAT_minus_ILP'] > 0 for p in selected),
            Both_Initial_Fallback=sum(p['SAT_Initial_Fallback'] and p['ILP_Initial_Fallback'] for p in selected),
            Max_Abs_Delta_LB=max((abs(p['Delta_LB_SAT_minus_ILP']) for p in selected), default=0),
            Max_Abs_Delta_UB=max((abs(p['Delta_UB_SAT_minus_ILP']) for p in selected), default=0)))
    return summaries


def collect(path):
    checked, _, _, metadata = audit(path)
    # The interpretation below was reviewed against the original worker: one
    # initial incumbent followed by a final result, without progress messages.
    expected = 'a5c54bd945ed35f385a379252a7dac6f6eeaf43a9fc12990394fa1a34ef07760'
    if source_digest() != metadata['source_sha256'] or metadata['source_sha256'] != expected:
        raise ValueError('use the matching archived initial/final-message source checkout for this audit')
    cases, _, _, _ = analyze(checked)
    open_keys = {(r['Instance'], r['h'], r['k']) for r in cases if r['Evidence'] == 'OPEN'}
    raw = {r['Graph']: r for r in csv.DictReader(path.open())}
    records = {r['Graph']: r for r in map(json.loads, path.with_suffix('.witnesses.jsonl').read_text().splitlines())}
    graphs = {name: graph for name, _, graph in general_pilot()}
    initial = {}
    rows = []
    for row in checked:
        key = (row['Instance'], row['h'], row['k'])
        if key not in initial:
            graph = graphs[key[0]]
            initial[key] = (*greedy_labeling(graph, *key[1:]), lower_bound(graph, *key[1:]))
        source = raw[row['Graph']]
        rows.append(dict(row, Termination=source['Termination'], Open_Instance=key in open_keys,
                         Initial_Fallback=initial_fallback(source, records[row['Graph']]['result'], initial[key])))
    pairs = pair_rows(rows)
    return rows, pairs, summarize(pairs), metadata


def export(path, output_root):
    rows, pairs, summary, metadata = collect(path)
    sources = [Path(__file__).resolve(), ROOT/'scripts/analyze_confirmation_gaps.py',
               ROOT/'scripts/build_confirmation_report.py', ROOT/'scripts/audit_general_pilot.py']
    identity = dict(inputs={str(p.relative_to(ROOT)): digest(p) for p in
                           (path, path.with_suffix('.metadata.json'), path.with_suffix('.witnesses.jsonl'))},
                    analysis_sources={str(p.relative_to(ROOT)): digest(p) for p in sources},
                    matched_benchmark_source_sha256=metadata['source_sha256'])
    version = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16]
    output_root.mkdir(parents=True, exist_ok=True)
    output = output_root/version
    counts = dict(BoundsOpenInstances=summary[1]['Instances'], BoundsOpenPairs=summary[1]['Repeat_Pairs'],
                  BoundsOpenFallbackPairs=summary[1]['Both_Initial_Fallback'],
                  BoundsFallbackObservations=sum(r['Initial_Fallback'] for r in rows))
    if output.exists():
        verify_cache(output, identity)
        return output
    temp = Path(tempfile.mkdtemp(prefix='.building-', dir=output_root))
    try:
        write_csv(temp/'paired_bounds.csv', pairs)
        write_csv(temp/'unresolved_pairs.csv', [r for r in pairs if r['Open_Instance']])
        write_csv(temp/'summary.csv', summary)
        provenance = [dict(Graph=r['Graph'], Instance=r['Instance'], h=r['h'], k=r['k'],
                           Method=r['Method'], Repeat=r['Repeat'], Status=r['Status'],
                           Termination=r['Termination'], Initial_Fallback=r['Initial_Fallback']) for r in rows]
        write_csv(temp/'capture_provenance.csv', provenance)
        table = [r'\begin{tabular}{lrrrrrr}', r'\toprule',
                 r'Subset & Pairs & LB: SAT & LB: equal & LB: ILP & UB: equal & Both initial\\', r'\midrule']
        for r in summary:
            table.append(' & '.join(str(r[k]) for k in ('Scope', 'Repeat_Pairs', 'SAT_Tighter_LB',
                         'Equal_LB', 'ILP_Tighter_LB', 'Equal_UB', 'Both_Initial_Fallback'))+r'\\')
        (temp/'comparison.tex').write_text('\n'.join([*table, r'\bottomrule', r'\end{tabular}'])+'\n')
        (temp/'counts.tex').write_text(''.join(f'\\newcommand{{\\{k}}}{{{v}}}\n' for k, v in counts.items()))
        (temp/'README.md').write_text('''# Recorded bounds and timeout provenance

This report compares CaDiCaL and Gurobi on the completed confirmation cohort.
ALL is 117 graph/(h,k) instances with 351 repeat pairs; OPEN selects the 21
instances whose joint interval remains open, giving 63 repeat pairs. This is
a post-hoc subset. Repetitions are not independent graphs. No new solver runs
or source-result modifications occur.

## Main finding and interpretation

All 63 OPEN pairs have identical recorded lower and upper bounds. Both sides
in all 63 pairs are initial fallbacks after WALL_TIMEOUT. The graph, full
labeling, greedy upper bound and initial lower bound were regenerated and
compared with each saved result. The benchmark source fingerprint matches
the archived run and the reviewed initial/final-message implementation.

Across the complete cohort, all 186 FEASIBLE observations are also initial
fallbacks. The native solvers may have made progress that was not transmitted
before the parent terminated them. An initial labeling that is retrospectively
optimal was supplied by the shared greedy routine; it is not evidence that
SAT produced that labeling through search. Bounds remain mathematically valid.

Equality of these stored intervals therefore does not establish equivalent
native solver bound quality, runtime, or overall effectiveness. Recorded OPT
coverage remains separate: SAT 77/117 and ILP 94/117 instances OPT in all three
runs. No formal equivalence test or margin has been specified. The original
measurements describe the complete wrapper under its capture policy.

## Files and columns

- paired_bounds.csv: all 351 matched pairs, keyed by Instance/h/k/Repeat;
  Group separates ER probabilities. Open_Instance selects the OPEN subset.
  SAT_LB/ILP_LB are recorded lower bounds; SAT_UB/ILP_UB are validated witness
  spans. Status and Termination retain the original run values. Initial_Fallback
  means the original initial-only snapshot was retained after external timeout.
  A returned OPT result equal to greedy is not classified as a fallback.
- Delta_LB_SAT_minus_ILP: positive favors SAT; negative favors ILP.
  Delta_UB_SAT_minus_ILP: negative favors SAT; positive favors ILP. Both are
  absolute differences in label units, not gaps to the unknown optimum.
- unresolved_pairs.csv: all 63 OPEN pairs, same schema; no case is omitted
  based on the direction of the comparison.
- summary.csv: Scope, Instances, Repeat_Pairs; counts of tighter/equal lower
  bounds and better/equal upper bounds, Both_Initial_Fallback, and maximum
  absolute differences. For each bound, SAT/equal/ILP counts sum to Repeat_Pairs.
  Counts describe recorded pipeline outputs, not unseen native solver progress.
- capture_provenance.csv: 702 observations with original identity, status,
  termination, and audited Initial_Fallback flag.
- comparison.tex and counts.tex: manuscript table and numerical macros.
- sources.json: input/output hashes, analysis code hashes, and the exact
  archived benchmark source fingerprint used to interpret message capture.

## Consequences for further experiments

The current graph families are retained. To compare bound quality at timeout,
a new capture protocol must transmit validated incumbent and lower-bound
updates while search runs, record their sources/timestamps, and preserve the
last received update on interruption. SAT UNSAT/SAT span completions and native
MILP primal/dual information need separate adapters and validation. Checking
only the final result is insufficient. Such a change requires tests and a new
run/version; missing old progress cannot be recovered by re-exporting this CSV.

Do not overwrite or resume this completed run to manufacture missing progress.
''')
        (temp/'sources.json').write_text(json.dumps(dict(identity=identity, counts=counts,
            outputs_sha256={p.name: digest(p) for p in temp.iterdir()}), indent=2)+'\n')
        temp.rename(output)
    except BaseException:
        shutil.rmtree(temp)
        raise
    return output


if __name__ == '__main__':
    output = export(ROOT/'results/runs/general_confirm_r1.csv', ROOT/'results/analysis/unresolved_bounds')
    relative = output.relative_to(ROOT).as_posix()
    wrapper = ROOT/'paper/generated/unresolved_bounds.tex'
    text = (f'\\input{{{relative}/counts.tex}}\n'
            f'\\newcommand{{\\BoundsReportDir}}{{{relative}}}\n')
    if not wrapper.exists() or wrapper.read_text() != text:
        wrapper.write_text(text)
    print(f'Audited recorded bounds and initial-fallback provenance: {relative}')
