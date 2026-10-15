"""Compact RQ3/RQ4 tables from archived evidence; no solver or CNF reconstruction."""
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil
import statistics
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.build_confirmation_report import digest, verify_cache, write_csv
from scripts.summarize_symmetry import read_run, summarize
from scripts.certificate_support import classify, counts as support_counts

PROGRESS = ROOT/'results/analysis/progress_confirmation/e8aaee5841468f67'
CONSTRUCTION = ROOT/'results/analysis/color_order/2d62af353a1756ae'
CLIQUE = ROOT/'results/analysis/clique_certificates/cc0e412739ccc8d2'
FAMILIES = ('C', 'CxC', 'CxP', 'PxP', 'CoC', 'CoP', 'PoC', 'PoP')
LABELS = {'C': r'$C_n$', **{
    f'{a}{op}{b}': f'${a}_n' + (r'\mathbin{\square}' if op == 'x' else r'\circ ') + f'{b}_m$'
    for a in 'CP' for b in 'CP' for op in 'xo'}}


def symmetry_summary(rows):
    """Count unresolved pairs; report sizes/times only on jointly optimal pairs."""
    summaries = {r['Family']: r for r in summarize(rows)}
    result = []
    for family in FAMILIES:
        if family not in summaries:
            continue
        group = [r for r in rows if r['Family'] == family]
        paired = [r for r in group if r['Status_Base'] == r['Status_Sym'] == 'OPT']
        rule = {'C': 'root=0+order', 'CxC': 'order', 'CxP': 'order',
                'CoC': 'order', 'CoP': 'order'}.get(family, 'none')
        if any(r['Symmetry_Rule'] != rule for r in group):
            raise ValueError('unexpected symmetry rule')
        if any(int(r['Var_Base']) <= 0 or r['Clause_Base'] <= 0 for r in paired):
            raise ValueError('percentage reduction requires positive baseline size')
        median_vars = statistics.median(100*(1-int(r['Var_Sym'])/int(r['Var_Base']))
                                         for r in paired) if paired else None
        summary = summaries[family]
        result.append(dict(Family=family, Rule=rule, Pairs=len(group),
            Joint_OPT=len(paired), Unresolved=len(group)-len(paired),
            Median_Variable_Reduction_Pct=median_vars,
            Median_Clause_Reduction_Pct=summary['Median_Paired_Clause_Reduction_Pct'],
            Fewer=sum(r['Clause_Sym'] < r['Clause_Base'] for r in paired),
            Equal=sum(r['Clause_Sym'] == r['Clause_Base'] for r in paired),
            More=sum(r['Clause_Sym'] > r['Clause_Base'] for r in paired),
            Median_Time_Base_Over_Sym=summary['Median_Paired_Speedup']))
    return result


def runtime_summary(instances):
    """Median of per-instance three-run medians on the common all-OPT subset."""
    checked, seen = [], set()
    for row in instances:
        key = (row['Instance'], int(row['h']), int(row['k']))
        if key in seen:
            raise ValueError('duplicate graph/parameter instance')
        seen.add(key)
        record = {'V': int(row['V'])}
        for method in ('cadical', 'gurobi'):
            flag = str(row[method+'_All_OPT'])
            if flag not in {'True', 'False'}:
                raise ValueError('invalid all-three-OPT flag')
            record[method] = flag == 'True'
            if record[method]:
                time = float(row[method+'_Median_Seconds'])
                if not math.isfinite(time) or time < 0:
                    raise ValueError('invalid runtime')
                record[method+'_time'] = time
        checked.append(record)
    result = []
    for size in [*sorted({r['V'] for r in checked}), 'ALL']:
        group = [r for r in checked if size == 'ALL' or r['V'] == size]
        joint = [r for r in group if r['cadical'] and r['gurobi']]
        result.append(dict(V=size, Instances=len(group),
            SAT_All_OPT=sum(r['cadical'] for r in group),
            ILP_All_OPT=sum(r['gurobi'] for r in group), Joint_All_OPT=len(joint),
            SAT_Median_Seconds=statistics.median(r['cadical_time'] for r in joint) if joint else None,
            ILP_Median_Seconds=statistics.median(r['gurobi_time'] for r in joint) if joint else None))
    return result


def family_runtime_summary(instances):
    """Use the same all-three-OPT criterion, separating ER densities and h,k."""
    total = runtime_summary(instances)[-1]  # Also rejects cohort-wide duplicates.
    result = []
    keys = sorted({(r['Group'], int(r['h']), int(r['k'])) for r in instances})
    for group, h, k in keys:
        selected = [r for r in instances if (r['Group'], int(r['h']), int(r['k'])) == (group, h, k)]
        summary = runtime_summary(selected)[-1]
        summary.pop('V')
        result.append(dict(Group=group, h=h, k=k, **summary))
    total.pop('V')
    result.append(dict(Group='ALL', h='', k='', **total))
    return result


def symmetry_counters(rows):
    """Totals from complete, jointly optimal runs; never interpret partial zeros."""
    result = []
    for family in FAMILIES:
        selected = [r for r in rows if r['Family'] == family
                    and r['Status_Base'] == r['Status_Sym'] == 'OPT'
                    and r['Stats_Complete_Base'] == r['Stats_Complete_Sym'] == 'True']
        if not selected:
            continue
        values = {key: sum(int(r[key]) for r in selected)
                  for key in ('Conflicts_Base', 'Conflicts_Sym', 'Decisions_Base', 'Decisions_Sym')}
        if any(int(r[key]) < 0 for r in selected for key in values):
            raise ValueError('negative search counter')
        result.append(dict(Family=family, Complete_Pairs=len(selected), **values))
    return result


def certificate_closures(original, final):
    """All five closures relative to pooled v2; distinguish lower/upper changes."""
    previous = {r['Certificate_ID']: r for r in original}
    current = {r['Certificate_ID']: r for r in final}
    if len(previous) != len(original) or len(current) != len(final) or previous.keys() != current.keys():
        raise ValueError('closure cohorts do not match')
    result = []
    for key, row in current.items():
        before = previous[key]
        low, high = int(before['Original_LB']), int(before['Witness_UB'])
        final_low, final_high = int(row['Final_LB']), int(row['Final_UB'])
        if (row['Instance'], row['h'], row['k']) != (before['Instance'], before['h'], before['k']):
            raise ValueError('closure instance parameters differ')
        if final_high > high or final_low < low or final_low > final_high:
            raise ValueError('closure interval is not a valid refinement')
        if low < high and final_low == final_high:
            result.append(dict(Instance=row['Instance'], h=int(row['h']), k=int(row['k']),
                V=int(row['V']), Graph_Seed=int(row['Instance'].rsplit('seed', 1)[1]),
                Original_LB=low, Original_UB=high, Clique_LB=int(before['Clique_LB']),
                Final_Span=final_high, UB_Improvement=high-final_high,
                Witness='new construction' if final_high < high else 'stored solver'))
    return result


def read_csv(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def table(path, columns, heading, rows):
    path.write_text('\n'.join([r'\begin{tabular}{'+columns+'}', r'\toprule',
        heading+r'\\', r'\midrule', *[' & '.join(r)+r'\\' for r in rows],
        r'\bottomrule', r'\end{tabular}'])+'\n')


def export():
    # Check archived provenance, without pretending current code recreates old CNFs.
    inputs = {}
    archived = ROOT/'paper/generated/sources.json'
    for experiment in json.loads(archived.read_text())['experiments']:
        for name, expected in experiment['files_sha256'].items():
            path = ROOT/'results/runs'/name
            if digest(path) != expected:
                raise ValueError(f'archived symmetry input changed: {name}')
            inputs[str(path.relative_to(ROOT))] = expected
    inputs[str(archived.relative_to(ROOT))] = digest(archived)
    manifest = json.loads((PROGRESS/'sources.json').read_text())
    verify_cache(PROGRESS, manifest['identity'])
    for name, expected in manifest['identity']['inputs'].items():
        if digest(ROOT/name) != expected:
            raise ValueError('v2 source input changed')
        inputs[name] = expected
    inputs[str((PROGRESS/'sources.json').relative_to(ROOT))] = digest(PROGRESS/'sources.json')
    for report in (CONSTRUCTION, CLIQUE):
        saved = json.loads((report/'sources.json').read_text())
        verify_cache(report, saved['identity'])
        inputs[str((report/'sources.json').relative_to(ROOT))] = digest(report/'sources.json')
    for name, expected in json.loads((CONSTRUCTION/'sources.json').read_text())['identity']['reports'].items():
        if digest(ROOT/name/'sources.json') != expected:
            raise ValueError('construction input report changed')
    sources = [Path(__file__), ROOT/'scripts/summarize_symmetry.py',
               ROOT/'scripts/build_confirmation_report.py', ROOT/'scripts/certificate_support.py',
               ROOT/'scripts/verify_clique_certificate.py']
    identity = dict(kind='compact-research-tables-v2', inputs=inputs,
                    sources={str(p.relative_to(ROOT)): digest(p) for p in sources})
    version = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16]
    directory = ROOT/'paper/generated/submission_summary'
    directory.mkdir(parents=True, exist_ok=True)
    output = directory/version
    if output.exists():
        verify_cache(output, identity)
    else:
        rows = read_run(ROOT/'results/runs/cycles_main_r1.csv') + read_run(ROOT/'results/runs/products_main_r1.csv')
        symmetry = symmetry_summary(rows)
        instances = read_csv(PROGRESS/'instances.csv')
        runtime = runtime_summary(instances)
        family_runtime = family_runtime_summary(instances)
        counters = symmetry_counters(rows)
        final = read_csv(CONSTRUCTION/'instances.csv')
        support = classify([json.loads(line) for line in (CONSTRUCTION/'certificates.jsonl').read_text().splitlines()], final)
        support_totals = support_counts(support)
        closures = certificate_closures(read_csv(CLIQUE/'instances.csv'), final)
        if (len(rows), sum(r['Joint_OPT'] for r in symmetry)) != (496, 494):
            raise ValueError('unexpected archived symmetry coverage')
        if [runtime[-1][k] for k in ('Instances', 'SAT_All_OPT', 'ILP_All_OPT', 'Joint_All_OPT')] != [117,77,91,74]:
            raise ValueError('unexpected v2 coverage')
        if (support_totals['Independent'], support_totals['SolverDependent'], len(closures)) != (90,11,5):
            raise ValueError('unexpected mathematical support or new closures')
        temporary = Path(tempfile.mkdtemp(prefix='.building-', dir=directory))
        try:
            write_csv(temporary/'symmetry.csv', symmetry)
            write_csv(temporary/'runtime.csv', runtime)
            write_csv(temporary/'family_runtime.csv', family_runtime)
            write_csv(temporary/'symmetry_counters.csv', counters)
            write_csv(temporary/'certificate_support.csv', support)
            write_csv(temporary/'five_closures.csv', closures)
            (temporary/'counts.tex').write_text(''.join(
                f'\\newcommand{{\\Support{key}}}{{{value}}}\n' for key, value in support_totals.items()))
            fmt = lambda v, digits: '--' if v is None else f'{v:.{digits}f}'
            body = []
            for row in symmetry:
                rule = {'root=0+order': 'R+O', 'order': 'O', 'none': '--'}[row['Rule']]
                body.append([LABELS[row['Family']], rule, f"{row['Joint_OPT']}/{row['Pairs']}",
                    fmt(row['Median_Variable_Reduction_Pct'],2), fmt(row['Median_Clause_Reduction_Pct'],2),
                    '/'.join(str(row[k]) for k in ('Fewer','Equal','More')),
                    fmt(row['Median_Time_Base_Over_Sym'],3)])
            table(temporary/'symmetry.tex', '@{}llrrrrr@{}',
                  r'Family & Rule & OPT/pairs & $\Delta V\,(\%)$ & $\Delta C\,(\%)$ & $C_S<C_B$/=/> & $t_B/t_S$', body)
            table(temporary/'runtime.tex','@{}lrrrrrr@{}',
                  r'$|V|$ & Cases & SAT OPT & ILP OPT & Joint & SAT (s) & ILP (s)',
                  [[str(r[k]) for k in ('V','Instances','SAT_All_OPT','ILP_All_OPT','Joint_All_OPT')]
                   +[fmt(r[k],3) for k in ('SAT_Median_Seconds','ILP_Median_Seconds')] for r in runtime])
            table(temporary/'family_runtime.tex', '@{}llrrrrrr@{}',
                  r'Family & $(h,k)$ & Cases & SAT OPT & ILP OPT & Joint & SAT (s) & ILP (s)',
                  [[r['Group'].replace('PxP', r'$P_n\square P_m$').replace('tree', 'Tree'),
                    f"$({r['h']},{r['k']})$" if r['h'] != '' else '--']
                   +[str(r[k]) for k in ('Instances','SAT_All_OPT','ILP_All_OPT','Joint_All_OPT')]
                   +[fmt(r[k],3) for k in ('SAT_Median_Seconds','ILP_Median_Seconds')] for r in family_runtime])
            table(temporary/'five_closures.tex', '@{}rrrrrrl@{}',
                  r'$|V|$ & Seed & V2 interval & Clique LB & Final & UB gain & Witness',
                  [[str(r['V']), str(r['Graph_Seed']), f"$[{r['Original_LB']},{r['Original_UB']}]$",
                    str(r['Clique_LB']), str(r['Final_Span']), str(r['UB_Improvement']), r['Witness']]
                   for r in closures])
            table(temporary/'symmetry_counters.tex', '@{}lrrrrr@{}',
                  r'Family & Pairs & Conflicts B & Conflicts S & Decisions B & Decisions S',
                  [[LABELS[r['Family']], str(r['Complete_Pairs'])]
                   +[str(r[k]) for k in ('Conflicts_Base','Conflicts_Sym','Decisions_Base','Decisions_Sym')]
                   for r in counters])
            (temporary/'README.md').write_text('''# Compact experimental tables

These tables answer the runtime/model-size and symmetry research questions
using existing experiments. No solver was called and no status was changed.

- symmetry.csv/.tex: eight families from cycles_main_r1/products_main_r1;
  496 configuration pairs, 494 jointly OPT. Reductions are medians of
  100*(Base-Sym)/Base at each row's common Count_Span, after common encoder
  preprocessing. Positive means smaller. Fewer/Equal/More compare clause
  counts; their sum equals Joint_OPT. Runtime is median of paired Base/Sym
  ratios, not the ratio of aggregate runtimes. Unresolved pairs are counted
  but excluded from these descriptive medians. Rule none repeats one model.
  Main_r1 has one measurement per configuration; no significance is inferred.
- runtime.csv/.tex: v2 instances grouped by vertex count. SAT/ILP OPT means
  optimal in all three repetitions. Times first take each instance's median
  over three repetitions, then the median across the SAME jointly all-OPT
  instances for both backends. These times exclude unresolved instances;
  the accompanying coverage columns keep that limitation visible. ALL is
  computed from all instances, not by averaging group medians.
- family_runtime.csv/.tex uses the same rule, grouped by family (with ER
  densities separated) and parameter pair. Missing common-subset runtimes
  are blank/--, never imputed as timeout or zero.
- symmetry_counters.csv/.tex sums conflicts and decisions across completed
  span trials and complete jointly OPT runs. Counts are totals, not medians,
  and do not isolate fixed-span solver effort or explain runtime causally.
- five_closures.csv/.tex gives all five closures relative to the original
  pooled v2 intervals. Two reuse stored labels and strengthen the lower
  bound; three use new labels, improving the upper bound by 2, 4 and 6.
- certificate_support.csv rechecks all 117 embedded graphs and labels with
  the standalone verifier, then degree/reference-grid bounds. A grid name
  alone is insufficient: its full edge set must match the formula's domain.
  Of 101 closed instances, 90 have mathematical support (61 theoretical-bound
  matches + 53 clique matches - 24 overlapping cases). The remaining 11 use
  recorded solver lower bounds. This classifies evidence, not actual optima
  among the 16 open instances. counts.tex exports this checked partition.

Symmetry uses historical Glucose runs, with 60s cycle and 180s product
budgets. V2 uses CaDiCaL/Gurobi and 30s, symmetry disabled. Timings and
statuses are never pooled across these protocols. Recorded CNF counts are
summarized; reproducing those historical CNFs requires the matching source.
Input and output fingerprints are in sources.json. Existing output edits
are rejected. Regenerate with scripts/export_submission_tables.py.
''')
            (temporary/'sources.json').write_text(json.dumps(dict(identity=identity,
                counts={'symmetry_pairs': len(rows),
                        'joint_symmetry_opt': sum(r['Joint_OPT'] for r in symmetry),
                        'v2_instances': runtime[-1]['Instances'],
                        'joint_v2_opt': runtime[-1]['Joint_All_OPT'], **support_totals},
                outputs_sha256={p.name: digest(p) for p in temporary.iterdir()}),indent=2)+'\n')
            temporary.rename(output)
        except BaseException:
            shutil.rmtree(temporary)
            raise
    relative = output.relative_to(ROOT).as_posix()
    (ROOT/'paper/generated/submission_summary.tex').write_text(
        '% Generated by scripts/export_submission_tables.py\n'
        f'\\newcommand{{\\SubmissionSummaryDir}}{{{relative}}}\n'
        f'\\input{{{relative}/counts.tex}}\n')
    return output


if __name__ == '__main__':
    print(export())
