"""Publish audited v2 results without merging the interrupted run or v1 data."""
import argparse
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
from scripts.summarize_progress_run import export
from scripts.build_confirmation_report import digest, verify_cache


def read_rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def publish(path):
    report = export(path, ROOT/'results/analysis/progress_confirmation')
    observations = read_rows(report/'observations.csv')
    instances = read_rows(report/'instances.csv')
    summary = read_rows(report/'summary.csv')
    opened = next(r for r in summary if r['Scope']=='OPEN')
    counts = dict(ProgressObservations=len(observations), ProgressInstances=len(instances),
                  ProgressJointStable=sum(all(r[m+'_All_OPT']=='True' for m in ('cadical','gurobi')) for r in instances),
                  ProgressOpen=int(opened['Instances']), ProgressOpenPairs=int(opened['Repeat_Pairs']),
                  ProgressOpenSATUB=int(opened['SAT_Better_UB']), ProgressOpenILPUB=int(opened['ILP_Better_UB']),
                  ProgressOpenEqualUB=int(opened['Equal_UB']), ProgressOpenILPLB=int(opened['ILP_Tighter_LB']),
                  ProgressOpenEqualLB=int(opened['Equal_LB']), ProgressMaxUB=int(opened['Max_Abs_Delta_UB']),
                  ProgressMaxLB=int(opened['Max_Abs_Delta_LB']))
    coverage = []
    for method, prefix in [('cadical','SAT'), ('gurobi','ILP')]:
        selected = [r for r in observations if r['Method']==method]
        optimal = sum(r['Status']=='OPT' and r['Within_Budget']=='True' for r in selected)
        stable = sum(r[method+'_All_OPT']=='True' for r in instances)
        feasible = sum(r['Status']=='FEASIBLE' for r in selected)
        improved = sum(r['Status']=='FEASIBLE' and int(r['UB_Improvement'])>0 for r in selected)
        counts.update({f'Progress{prefix}Opt':optimal, f'Progress{prefix}Stable':stable,
                       f'Progress{prefix}Feasible':feasible, f'Progress{prefix}ImprovedUB':improved})
        coverage.append((prefix, optimal, stable, feasible, improved))
    returned_feasible = [r for r in observations if r['Status']=='FEASIBLE' and r['Termination']=='RETURNED']
    counts['ProgressReturnedFeasible'] = len(returned_feasible)
    counts['ProgressClosed'] = len(instances)-counts['ProgressOpen']
    identity = dict(report_sources_sha256=digest(report/'sources.json'),
                    report=str(report.relative_to(ROOT)), exporter_sha256=digest(Path(__file__)))
    version=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()[:16]
    root=ROOT/'paper/generated/progress_confirmation'
    root.mkdir(parents=True,exist_ok=True)
    output=root/version
    if output.exists():
        verify_cache(output,identity)
    else:
        temporary=Path(tempfile.mkdtemp(prefix='.building-',dir=root))
        try:
            (temporary/'counts.tex').write_text(''.join(f'\\newcommand{{\\{name}}}{{{value}}}\n' for name,value in counts.items()))
            lines=[r'\begin{tabular}{lrrrr}',r'\toprule',r'Backend & OPT runs & All-three OPT & FEAS runs & Improved UB$^*$ \\',r'\midrule']
            lines += [f'{m} & {o}/351 & {s}/117 & {f} & {u}/{f} \\\\' for m,o,s,f,u in coverage]
            lines += [r'\bottomrule',r'\end{tabular}']
            (temporary/'coverage.tex').write_text('\n'.join(lines)+'\n')
            lines=[r'\begin{tabular}{lrrrrrrr}',r'\toprule',r'Scope & Pairs & \multicolumn{3}{c}{Higher LB} & \multicolumn{3}{c}{Lower UB} \\',r'& & SAT & Equal & ILP & SAT & Equal & ILP \\',r'\midrule']
            for row in summary:
                values=[row[k] for k in ('Repeat_Pairs','SAT_Tighter_LB','Equal_LB','ILP_Tighter_LB','SAT_Better_UB','Equal_UB','ILP_Better_UB')]
                lines.append(('All instances' if row['Scope']=='ALL' else 'Open instances')+' & '+' & '.join(values)+r' \\')
            lines += [r'\bottomrule',r'\end{tabular}']
            (temporary/'bounds.tex').write_text('\n'.join(lines)+'\n')
            text=f'''# Completed progress-capture confirmation

Source: `{Path(path).name}`. Audited report: `{report.relative_to(ROOT)}`.
The interrupted `general_progress_v2_20261007T043750933380Z.csv` (464 observations)
is retained separately and contributes no observations to this comparison.

The complete run contains {len(observations)} observations on {len(instances)} graph/parameter
instances, with three repetitions per backend and a 30-second external limit.
All recorded witnesses, progress ledgers, and cross-backend/repetition bounds
passed the audit. No contradictory reported optima were found. This validates
feasibility and consistency; it does not independently check UNSAT certificates.

| Measure | CaDiCaL | Gurobi |
|---|---:|---:|
| OPT observations within budget | {counts['ProgressSATOpt']}/351 | {counts['ProgressILPOpt']}/351 |
| Instances OPT in all three repetitions | {counts['ProgressSATStable']}/117 | {counts['ProgressILPStable']}/117 |
| FEASIBLE observations | {counts['ProgressSATFeasible']} | {counts['ProgressILPFeasible']} |
| FEASIBLE observations with UB improved over initialization | {counts['ProgressSATImprovedUB']} | {counts['ProgressILPImprovedUB']} |

There are {counts['ProgressJointStable']} instances OPT in all three runs for both backends.
Pooling this run's valid solver intervals closes {counts['ProgressClosed']} instance intervals;
{counts['ProgressOpen']} remain open. Pooling is post-hoc evidence, not a single timed solver run.

On the {counts['ProgressOpenPairs']} repeat pairs from those open instances:

- SAT has a better upper bound in {counts['ProgressOpenSATUB']} pairs, Gurobi in {counts['ProgressOpenILPUB']}, with {counts['ProgressOpenEqualUB']} ties.
- Gurobi has a stronger lower bound in {counts['ProgressOpenILPLB']} pairs, with {counts['ProgressOpenEqualLB']} ties and none favoring SAT.
- Maximum absolute differences are {counts['ProgressMaxUB']} label units for UB and {counts['ProgressMaxLB']} for LB.
- The {counts['ProgressOpenPairs']} pairs represent {counts['ProgressOpen']} instances measured three times, not independent inputs.

These results support greater Gurobi optimality coverage on this cohort and
complementary feasible-solution quality on the unresolved subset. They do not
support a blanket claim of equivalent effectiveness or consistently small
bound differences. Keep both primal quality and lower-bound/proof quality.

Returned FEASIBLE observations: {len(returned_feasible)}. Their native Gurobi
termination code was not retained by the runner, so the reason for the return
is unknown. They remain FEASIBLE, not OPT or external timeouts:
'''
            for row in returned_feasible:
                text+=f"\n- `{row['Graph']}`: [{row['Recorded_LB']}, {row['Witness_Span']}], {float(row['Wall_Time']):.3f} seconds.\n"
            text+='''
No rerun is needed to recover the interrupted file: use the complete run above.
Keep v1 results separate because capture and timing overhead differ. The next
research decision is interpretation of this SAT–ILP comparison with the supervisor;
a new graph family or GA benchmark is not automatically required.
'''
            (temporary/'README.md').write_text(text)
            (temporary/'sources.json').write_text(json.dumps(dict(identity=identity,counts=counts,
                outputs_sha256={p.name:digest(p) for p in temporary.iterdir()}),indent=2)+'\n')
            temporary.rename(output)
        except BaseException:
            shutil.rmtree(temporary)
            raise
    relative=output.relative_to(ROOT).as_posix()
    (ROOT/'paper/generated/progress_confirmation.tex').write_text(
        f'\\input{{{relative}/counts.tex}}\n\\newcommand{{\\ProgressReportDir}}{{{relative}}}\n')
    print(f'Published progress-capture tables: {relative}')
    return output


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,default=ROOT/'results/runs/general_progress_v2_20261007T062406751526Z.csv')
    args=parser.parse_args()
    publish(args.input)
