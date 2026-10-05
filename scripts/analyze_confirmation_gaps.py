"""Analyze unresolved intervals and incumbent quality in the fixed confirmation.

This is post-hoc evidence aggregation, not another solver or timed experiment.
Recorded statuses and all source artifacts remain unchanged.
"""
import argparse
from collections import Counter, defaultdict
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
from scripts.build_confirmation_report import (
    METHODS, audit, digest, group_name, verify_cache, write_csv,
)


def analyze(checked):
    """Combine six audited observations per instance; never relabel OPT.

    A lower bound from a solver is accepted as recorded, not independently
    certified here. Theory bounds and validated witness spans are additional
    evidence. A strictly worse witness is detectable even for an open optimum.
    """
    by_instance = defaultdict(list)
    for row in checked:
        by_instance[row['Instance'], row['h'], row['k']].append(row)
    if not by_instance:
        raise ValueError('no audited observations')
    cases, observations = [], []
    expected = {(m, r) for m in METHODS for r in range(3)}
    for (name, h, k), rows in sorted(by_instance.items()):
        if len(rows) != 6 or {(r['Method'], r['Repeat']) for r in rows} != expected:
            raise ValueError('expected exactly six unique backend/repeat observations')
        references = {(r['Theory_LB'], r['Theory_UB'], r['Exact_Reference']) for r in rows}
        if len(references) != 1 or len({(r['Family'], r['V'], r['E']) for r in rows}) != 1:
            raise ValueError('instance or reference metadata differs across observations')
        theory_lb, theory_ub, exact = references.pop()
        for row in rows:
            if (row['Status'] not in {'OPT', 'FEASIBLE'}
                    or not 0 <= row['Recorded_LB'] <= row['Witness_Span'] <= row['Span']
                    or row['Status'] == 'OPT' and not
                    row['Recorded_LB'] == row['Witness_Span'] == row['Span']):
                raise ValueError('invalid recorded status or bounds')
        lower = max(theory_lb, max(r['Recorded_LB'] for r in rows))
        upper = min(r['Witness_Span'] for r in rows)
        if lower > upper or lower > theory_ub or exact is not None and not lower <= exact <= upper:
            raise ValueError('combined bounds contradict witnesses or reference')
        if upper == theory_lb:
            basis = 'THEORY_MATCH'
        elif any(r['Status'] == 'OPT' for r in rows):
            basis = 'RECORDED_OPT'
        elif lower == upper:
            basis = 'COMBINED_CLOSURE'
        else:
            basis = 'OPEN'
        case = dict(Instance=name, Group=group_name(rows[0]), h=h, k=k,
                    V=rows[0]['V'], E=rows[0]['E'], Theory_LB=theory_lb,
                    Exact_Reference=exact, Combined_LB=lower, Best_Witness_UB=upper,
                    Absolute_Gap=upper-lower, Evidence=basis,
                    Lower_Sources=';'.join(
                        (['theory'] if theory_lb == lower else []) +
                        [r['Graph'] for r in rows if r['Recorded_LB'] == lower]),
                    Upper_Sources=';'.join(r['Graph'] for r in rows if r['Witness_Span'] == upper))
        for method in METHODS:
            selected = [r for r in rows if r['Method'] == method]
            case[method+'_OPT_Within_Budget'] = sum(
                r['Status'] == 'OPT' and r['Within_Budget'] for r in selected)
            case[method+'_Best_Witness_UB'] = min(r['Witness_Span'] for r in selected)
        cases.append(case)
        for row in sorted(rows, key=lambda r: (r['Method'], r['Repeat'])):
            span = row['Witness_Span']
            quality = ('KNOWN_OPTIMAL' if lower == upper == span else
                       'KNOWN_SUBOPTIMAL' if span > upper else 'UNRESOLVED')
            observations.append(dict(
                Graph=row['Graph'], Instance=name, Group=case['Group'], h=h, k=k,
                Method=row['Method'], Repeat=row['Repeat'], Status=row['Status'],
                Within_Budget=row['Within_Budget'], Recorded_LB=row['Recorded_LB'],
                Witness_Span=span, Combined_LB=lower, Best_Witness_UB=upper,
                Quality=quality, Excess_Lower=span-upper, Excess_Upper=span-lower))
    summary = []
    for group, h, k in sorted({(r['Group'], r['h'], r['k']) for r in cases}):
        selected = [r for r in cases if (r['Group'], r['h'], r['k']) == (group, h, k)]
        count = Counter(r['Evidence'] for r in selected)
        summary.append(dict(Group=group, h=h, k=k, Instances=len(selected),
                            Theory_Match=count['THEORY_MATCH'], Recorded_OPT=count['RECORDED_OPT'],
                            Combined_Closure=count['COMBINED_CLOSURE'], Open=count['OPEN'],
                            Max_Open_Gap=max((r['Absolute_Gap'] for r in selected), default=0)))
    quality = []
    for method in METHODS:
        selected = [r for r in observations if r['Method'] == method and r['Status'] == 'FEASIBLE']
        count = Counter(r['Quality'] for r in selected)
        quality.append(dict(Method=method, FEASIBLE=len(selected),
                            Known_Optimal=count['KNOWN_OPTIMAL'], Known_Suboptimal=count['KNOWN_SUBOPTIMAL'],
                            Unresolved=count['UNRESOLVED']))
    return cases, observations, summary, quality


def artifacts(output, checked):
    cases, observations, summary, quality = analyze(checked)
    unresolved = [r for r in cases if r['Evidence'] == 'OPEN']
    for name, rows in [('instances', cases), ('observations', observations),
                       ('summary', summary), ('feasible_quality', quality)]:
        write_csv(output/f'{name}.csv', rows)
    # Retain the schema when every case is closed.
    import csv
    with (output/'unresolved.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(cases[0]))
        writer.writeheader()
        writer.writerows(unresolved)
    lines = [r'\begin{tabular}{llrrrr}', r'\toprule',
             r'Family & $(h,k)$ & Cases & Theory & Other closed & Open\\', r'\midrule']
    for r in summary:
        lines.append(f"{r['Group']} & $({r['h']},{r['k']})$ & {r['Instances']} & "
                     f"{r['Theory_Match']} & {r['Recorded_OPT']+r['Combined_Closure']} & {r['Open']}"+r'\\')
    (output/'summary.tex').write_text('\n'.join([*lines, r'\bottomrule', r'\end{tabular}'])+'\n')
    lines = [r'\begin{tabular}{lrrrr}', r'\toprule',
             r'Backend & FEASIBLE & Optimal witness & Worse witness & Unresolved\\', r'\midrule']
    for r in quality:
        lines.append(' & '.join([r['Method'], *[str(r[x]) for x in
                     ('FEASIBLE', 'Known_Optimal', 'Known_Suboptimal', 'Unresolved')]])+r'\\')
    (output/'quality.tex').write_text('\n'.join([*lines, r'\bottomrule', r'\end{tabular}'])+'\n')
    counts = dict(GapInstances=len(cases), GapObservations=len(observations),
                  GapTheory=sum(r['Evidence'] == 'THEORY_MATCH' for r in cases),
                  GapRecorded=sum(r['Evidence'] == 'RECORDED_OPT' for r in cases),
                  GapCombined=sum(r['Evidence'] == 'COMBINED_CLOSURE' for r in cases),
                  GapClosed=len(cases)-len(unresolved), GapOpen=len(unresolved),
                  GapOpenMin=min((r['Absolute_Gap'] for r in unresolved), default=0),
                  GapOpenMax=max((r['Absolute_Gap'] for r in unresolved), default=0),
                  GapSATFeasibleOptimal=quality[0]['Known_Optimal'])
    (output/'counts.tex').write_text(''.join(f'\\newcommand{{\\{key}}}{{{value}}}\n' for key, value in counts.items()))
    (output/'README.md').write_text('''# Post-hoc optimality intervals and incumbent quality

This analysis revalidates all six observations per graph/(h,k) using the
confirmation checker. It does not run solvers, modify original statuses, pool
pilot data, or verify UNSAT certificates. The units are 117 instances and 702
observations in the fixed confirmation cohort, not 702 independent graphs.

For each instance, L is the maximum of applicable theoretical lower bounds
and recorded solver lower bounds over six runs; U is the smallest independently
validated witness span. These combined bounds did not necessarily arise in
one run or within one 30-second budget. Closing [L,U] is therefore not a new
single-run performance result. Solver lower bounds retain their original
trust assumptions. The theoretical upper bound is checked for contradictions
but is not substituted for U, which always has a stored witness.

## Files and definitions

- instances.csv: one row per Instance/h/k. Group separates ER probabilities;
  V/E count vertices/edges. Theory_LB and Exact_Reference are applicable
  mathematical references (blank Exact_Reference means no exact formula).
  Combined_LB=L, Best_Witness_UB=U, Absolute_Gap=U-L in label units.
  Lower_Sources lists theory and/or observation IDs attaining L; Upper_Sources
  lists observation IDs attaining U. Backend OPT_Within_Budget columns count
  original OPT runs within budget (0..3); Best_Witness_UB is that backend's
  best span over three runs. None is a new measured runtime.
- Evidence is assigned in this order: THEORY_MATCH when U=Theory_LB;
  RECORDED_OPT when a saved OPT result closes the interval; COMBINED_CLOSURE
  when L=U without either preceding category; otherwise OPEN. Categories are
  exclusive. Theory matches include exact-reference instances and cases where
  a general lower bound is attained; they do not establish a new family formula.
- unresolved.csv: all OPEN instances, with the same schema. No case is removed
  based on which backend performs better. These are candidates for further
  analysis, not evidence that their graph family is intrinsically hardest.
- observations.csv: original Graph ID, Method, Repeat, Status, Within_Budget,
  Recorded_LB, and validated Witness_Span, together with combined bounds.
  Quality=KNOWN_OPTIMAL when the witness attains a closed interval;
  KNOWN_SUBOPTIMAL when a strictly smaller stored valid witness exists;
  UNRESOLVED otherwise. The latter does not imply suboptimality. Quality is
  retrospective and does not replace the recorded solver status.
  If the witness span is u and the optimum is lambda, Excess_Lower=u-U and
  Excess_Upper=u-L bound u-lambda. They are absolute gaps, not percentages,
  statistical confidence intervals, or the commercial solver's MIP gap.
- summary.csv: counts by Group/h/k. Theory_Match, Recorded_OPT,
  Combined_Closure, Open partition Instances. Max_Open_Gap is the largest U-L,
  or zero if no open case exists.
- feasible_quality.csv: counts by backend restricted to original FEASIBLE
  observations. Known_Optimal, Known_Suboptimal, Unresolved partition FEASIBLE.
  Repetitions share graphs, so these are not independent sample counts.
- summary.tex, quality.tex, counts.tex: corresponding manuscript artifacts.
- sources.json: immutable input/source/environment hashes and output hashes.

Use `make gap-analysis` to regenerate or verify the report and build the PDF.
A source change creates a new version. Edited cached artifacts are rejected.
''')
    return counts


def publish(input_path, output_root):
    checked, _, _, _ = audit(input_path)
    inputs = [input_path, input_path.with_suffix('.metadata.json'), input_path.with_suffix('.witnesses.jsonl')]
    sources = [Path(__file__).resolve(), ROOT/'scripts/build_confirmation_report.py',
               ROOT/'scripts/audit_general_pilot.py', ROOT/'benchmarks/general_suite.py',
               ROOT/'src/core/graph_utils.py', ROOT/'src/core/parameters.py']
    def name(p):
        return p.relative_to(ROOT).as_posix() if p.is_relative_to(ROOT) else str(p)
    identity = dict(inputs={name(p): digest(p) for p in inputs},
                    sources={name(p): digest(p) for p in sources},
                    environment=dict(python=sys.version, networkx=nx.__version__))
    version = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16]
    output_root.mkdir(parents=True, exist_ok=True)
    output = output_root/version
    if output.exists():
        counts = verify_cache(output, identity)
    else:
        temp = Path(tempfile.mkdtemp(prefix='.building-', dir=output_root))
        try:
            counts = artifacts(temp, checked)
            (temp/'sources.json').write_text(json.dumps(dict(
                identity=identity, counts=counts,
                outputs_sha256={p.name: digest(p) for p in temp.iterdir()}), indent=2)+'\n')
            temp.rename(output)
        except BaseException:
            shutil.rmtree(temp)
            raise
    return output, counts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    path = ROOT/'results/runs/general_confirm_r1.csv'
    if args.check_only:
        checked, _, _, _ = audit(path)
        cases, _, _, _ = analyze(checked)
        print(f"Validated {len(cases)} instances; {sum(r['Evidence']=='OPEN' for r in cases)} open")
        return
    output, counts = publish(path, ROOT/'results/analysis/confirmation_gaps')
    relative = output.relative_to(ROOT).as_posix()
    wrapper = ROOT/'paper/generated/confirmation_gaps.tex'
    content = (f'% Generated by scripts/analyze_confirmation_gaps.py\n'
               f'\\input{{{relative}/counts.tex}}\n'
               f'\\newcommand{{\\GapReportDir}}{{{relative}}}\n')
    if not wrapper.exists() or wrapper.read_text() != content:
        wrapper.write_text(content)
    print(f"Validated {counts['GapObservations']} observations; {counts['GapClosed']} closed, "
          f"{counts['GapOpen']} open intervals. Report: {relative}")


if __name__ == '__main__':
    main()
