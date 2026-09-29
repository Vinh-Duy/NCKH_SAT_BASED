"""Audit the three-repeat confirmation and publish reproducible paper artifacts.

No SAT/ILP calls. Outputs are versioned by input/source hashes; reruns reuse
verified artifacts and never overwrite benchmark data or user-edited outputs.
"""
import argparse
from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import shutil
import statistics
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import networkx as nx
from benchmarks.general_suite import general_pilot, SUITE_NAME
from scripts.audit_general_pilot import check_observation, check_pairs

METHODS = ('cadical', 'gurobi')
GROUPS = ('tree', 'PxP', 'ER p=0.15', 'ER p=0.30', 'BA')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def group_name(row):
    if row['Family'] == 'ER':
        return f"ER p={float(row['Instance'].split('_p')[1].split('_')[0]):.2f}"
    return row['Family']


def summarize(checked):
    """Instances are graph/h/k; repeats are not independent graphs."""
    check_pairs(checked)
    by_instance = defaultdict(list)
    for row in checked:
        by_instance[row['Instance'], row['h'], row['k']].append(row)
    instance_rows = []
    for (name,h,k), rows in sorted(by_instance.items()):
        if len(rows) != 6 or {(r['Method'],r['Repeat']) for r in rows} != {(m,t) for m in METHODS for t in range(3)}:
            raise ValueError('each instance requires exactly three repeats of both backends')
        optima = {r['Span'] for r in rows if r['Status']=='OPT'}
        if len(optima) > 1:
            raise ValueError('optimal values disagree across repetitions')
        lower, upper = max(r['Recorded_LB'] for r in rows), min(r['Witness_Span'] for r in rows)
        if lower > upper:
            raise ValueError('cross-repeat bounds contradict witnesses')
        result = dict(Instance=name, Group=group_name(rows[0]), h=h, k=k, V=rows[0]['V'],
                      Combined_LB=lower, Best_Witness_Span=upper,
                      Exact_Reference=rows[0]['Exact_Reference'],
                      Reference_Matches=sum(r['Reference_Check']=='MATCH' for r in rows))
        for method in METHODS:
            selected = [r for r in rows if r['Method']==method]
            solved = [r for r in selected if r['Status']=='OPT' and r['Within_Budget']]
            times = [r['Wall_Time'] for r in selected]
            all_opt = len(solved)==3
            result.update({method+'_OPT_Repeats':len(solved), method+'_All_OPT':all_opt,
                           method+'_Median_Seconds':statistics.median(times) if all_opt else None,
                           method+'_Min_Seconds':min(times) if all_opt else None,
                           method+'_Max_Seconds':max(times) if all_opt else None})
        instance_rows.append(result)
    summary = []
    for h,k in sorted({(r['h'],r['k']) for r in checked}):
        for group in GROUPS:
            subset = [r for r in instance_rows if (r['Group'],r['h'],r['k'])==(group,h,k)]
            if not subset:
                continue
            observations = [r for r in checked if (group_name(r),r['h'],r['k'])==(group,h,k)]
            joint = [r for r in subset if all(r[m+'_All_OPT'] for m in METHODS)]
            row = dict(Group=group, h=h, k=k, Instances=len(subset), Paired_All_OPT=len(joint),
                       Exact_Reference_Instances=sum(r['Exact_Reference'] is not None for r in subset))
            for method in METHODS:
                row.update({method+'_OPT_Observations':sum(r['Method']==method and r['Status']=='OPT' and r['Within_Budget'] for r in observations),
                            method+'_FEASIBLE_Observations':sum(r['Method']==method and r['Status']=='FEASIBLE' for r in observations),
                            method+'_All_OPT_Instances':sum(r[method+'_All_OPT'] for r in subset),
                            method+'_Paired_Median_Seconds':statistics.median(r[method+'_Median_Seconds'] for r in joint) if joint else None})
            summary.append(row)
    return instance_rows, summary


def audit(path):
    path = Path(path)
    meta = json.loads(path.with_suffix('.metadata.json').read_text())
    config = meta['config']
    if (config['suite'] != SUITE_NAME or config['pairs'] != [[1,1],[2,1],[3,2]]
            or config['repeats'] != 3 or set(config['methods']) != set(METHODS)
            or config['timeout'] != 30 or config['symmetry'] is not False or config['ilp_threads'] != 1):
        raise ValueError('expected confirmation protocol: fixed cohort, three repeats, two backends, 30s, symmetry off')
    if meta['packages']['networkx'] != nx.__version__:
        raise ValueError('NetworkX version differs from the saved graph generator')
    cohort = {name:(family,graph) for name,family,graph in general_pilot()}
    expected = {f'{name}__h{h}_k{k}__r{repeat}__{method}' for name in cohort
                for h,k in config['pairs'] for repeat in range(3) for method in METHODS}
    with path.open(newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != meta['schema']:
            raise ValueError('CSV schema does not match metadata')
        rows = list(reader)
    records = [json.loads(line) for line in path.with_suffix('.witnesses.jsonl').read_text().splitlines()]
    witnesses = {r['Graph']:r for r in records}
    if len(rows)!=len(expected) or len(records)!=len(expected) or set(witnesses)!=expected or {r['Graph'] for r in rows}!=expected:
        raise ValueError('missing, duplicate or unexpected CSV/witness observations')
    checked = []
    for row in rows:
        if row['Graph'] != f"{row['Instance']}__h{row['h']}_k{row['k']}__r{row['Repeat']}__{row['Method']}":
            raise ValueError('CSV identity mismatch')
        family, graph = cohort[row['Instance']]
        checked.append(check_observation(row,witnesses[row['Graph']],graph,family,config))
    instances, summary = summarize(checked)
    return checked, instances, summary, meta


def write_csv(path, rows):
    with path.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)


def figures(output, checked, instances):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'text.usetex':False})
    fig, axes = plt.subplots(1,3,figsize=(12,3.8),sharey=True)
    for ax,(h,k) in zip(axes,[(1,1),(2,1),(3,2)]):
        subset=[r for r in instances if (r['h'],r['k'])==(h,k)]
        x=list(range(len(GROUPS)))
        for method,offset,color in [('cadical',-.18,'#2166ac'),('gurobi',.18,'#b35806')]:
            counts=[sum(r['Group']==g and r[method+'_All_OPT'] for r in subset) for g in GROUPS]
            bars=ax.bar([i+offset for i in x],counts,.35,label=method,color=color)
            for bar,n,g in zip(bars,counts,GROUPS):
                denominator=sum(r['Group']==g for r in subset)
                ax.text(bar.get_x()+bar.get_width()/2,n+.15,f'{n}/{denominator}',ha='center',fontsize=8)
        ax.set_xticks(x,['Tree','Grid','ER .15','ER .30','BA'],rotation=25)
        ax.set_title(f'L({h},{k})');ax.set_ylim(0,11);ax.grid(axis='y',alpha=.2)
    axes[0].set_ylabel('Instances OPT in all three repeats')
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='upper center',ncol=2)
    fig.tight_layout(rect=(0,0,1,.91))
    for ext in ('pdf','png'): fig.savefig(output/f'coverage.{ext}',dpi=300)
    plt.close(fig)
    fig, axes=plt.subplots(1,3,figsize=(12,3.8),sharex=True,sharey=True)
    markers=['o','s','^','v','D']
    for ax,(h,k) in zip(axes,[(1,1),(2,1),(3,2)]):
        n=0
        for group,marker in zip(GROUPS,markers):
            selected=[r for r in instances if (r['Group'],r['h'],r['k'])==(group,h,k)
                      and all(r[m+'_All_OPT'] for m in METHODS)]
            n+=len(selected)
            if not selected: continue
            x=[r['gurobi_Median_Seconds'] for r in selected];y=[r['cadical_Median_Seconds'] for r in selected]
            ax.errorbar(x,y,xerr=[[r['gurobi_Median_Seconds']-r['gurobi_Min_Seconds'] for r in selected],
                                  [r['gurobi_Max_Seconds']-r['gurobi_Median_Seconds'] for r in selected]],
                        yerr=[[r['cadical_Median_Seconds']-r['cadical_Min_Seconds'] for r in selected],
                              [r['cadical_Max_Seconds']-r['cadical_Median_Seconds'] for r in selected]],
                        fmt=marker,markersize=4,alpha=.7,linewidth=.6,label=group)
        ax.plot([.1,30],[.1,30],color='gray',linestyle='--',linewidth=.8)
        ax.set(xscale='log',yscale='log',xlim=(.1,30),ylim=(.1,30),title=f'L({h},{k}); {n}/39 jointly stable OPT',xlabel='Gurobi wall time (s)')
        ax.grid(alpha=.2)
    axes[0].set_ylabel('CaDiCaL wall time (s)')
    handles,labels=axes[0].get_legend_handles_labels()
    fig.legend(handles,labels,loc='upper center',ncol=5,fontsize=8)
    fig.tight_layout(rect=(0,0,1,.9))
    for ext in ('pdf','png'): fig.savefig(output/f'runtime.{ext}',dpi=300)
    plt.close(fig)


def artifacts(output, checked, instances, summary):
    for filename,rows in [('observations.csv',checked),('instances.csv',instances),('summary.csv',summary)]:
        write_csv(output/filename,rows)
    lines=[r'\begin{tabular}{llrrrrr}',r'\toprule',r'Family & $(h,k)$ & Cases & SAT OPT runs & ILP OPT runs & SAT all 3 & ILP all 3\\',r'\midrule']
    for r in summary:
        lines.append(' & '.join([r['Group'],f"$({r['h']},{r['k']})$",str(r['Instances']),
                     f"{r['cadical_OPT_Observations']}/{3*r['Instances']}",f"{r['gurobi_OPT_Observations']}/{3*r['Instances']}",
                     str(r['cadical_All_OPT_Instances']),str(r['gurobi_All_OPT_Instances'])])+r'\\')
    (output/'summary.tex').write_text('\n'.join([*lines,r'\bottomrule',r'\end{tabular}'])+'\n')
    lines=[r'\begin{tabular}{llrrr}',r'\toprule',r'Family & $(h,k)$ & Both all 3 OPT & SAT (s) & ILP (s)\\',r'\midrule']
    for r in summary:
        times=['--' if r[m+'_Paired_Median_Seconds'] is None else f"{r[m+'_Paired_Median_Seconds']:.3f}" for m in METHODS]
        lines.append(' & '.join([r['Group'],f"$({r['h']},{r['k']})$",str(r['Paired_All_OPT']),*times])+r'\\')
    (output/'timing.tex').write_text('\n'.join([*lines,r'\bottomrule',r'\end{tabular}'])+'\n')
    counts=dict(ConfirmObservations=len(checked),ConfirmInstances=len(instances),
                ConfirmSATOpt=sum(r['Method']=='cadical' and r['Status']=='OPT' and r['Within_Budget'] for r in checked),
                ConfirmILPOpt=sum(r['Method']=='gurobi' and r['Status']=='OPT' and r['Within_Budget'] for r in checked),
                ConfirmSATStable=sum(r['cadical_All_OPT'] for r in instances),
                ConfirmILPStable=sum(r['gurobi_All_OPT'] for r in instances),
                ConfirmJointStable=sum(all(r[m+'_All_OPT'] for m in METHODS) for r in instances),
                ConfirmReferenceInstances=sum(r['Exact_Reference'] is not None for r in instances),
                ConfirmReferenceMatches=sum(r['Reference_Check']=='MATCH' for r in checked),
                ConfirmFeasible=sum(r['Status']=='FEASIBLE' for r in checked),
                ConfirmOutsideBudget=sum(r['Status']=='OPT' and not r['Within_Budget'] for r in checked))
    (output/'counts.tex').write_text(''.join(f'\\newcommand{{\\{key}}}{{{value}}}\n' for key,value in counts.items()))
    (output/'README.md').write_text('''# General confirmation: three repeats

Input: results/runs/general_confirm_r1.csv and its metadata/witness sidecars.
No solver reruns, original status changes, or independent UNSAT proof checks.
The audit regenerates graphs, checks shortest-path labeling constraints and
reference bounds, then checks consistency across backends and repetitions.

- observations.csv: 702 individual backend/repeat observations, validated with
  the pilot checker; Recorded_LB and Span are preserved. Theory_Optimal is a
  separate witness-vs-theory certificate, not a rewritten solver status.
- instances.csv: 117 distinct graph/h/k tasks. OPT_Repeats counts OPT within
  budget (0..3). All_OPT means all three. Median/Min/Max_Seconds exist only
  when all three repetitions were OPT within budget. They describe repeats
  of one graph, not variation across graphs. Combined_LB and Best_Witness_Span
  combine all six observations: not bounds obtained in one 30-second run.
- summary.csv: Group/h/k summaries, separating ER probabilities. Instances
  is the number of graph/h/k tasks; OPT_Observations counts repetitions;
  All_OPT_Instances counts tasks solved optimally in all three repeats.
  Paired_All_OPT requires both backends to meet this condition.
  Paired_Median_Seconds is the median of per-instance three-repeat medians
  on that common subset only (selection bias). Missing values are not zero.
  Exact_Reference_Instances counts applicable formulas, not new theorems.
- coverage.pdf/png: all-three-OPT tasks / total tasks in each group.
- runtime.pdf/png: one point per jointly all-three-OPT task; medians and
  min--max repeat bars (not confidence intervals); below diagonal favors SAT.
- summary.tex, timing.tex, counts.tex: manuscript tables/macros from this audit.
- sources.json: input, source and environment fingerprint plus output hashes.

The exact review dated 20260928 and the one-repeat pilot stay separate.
Missing/duplicate records, invalid labels or conflicting OPT results stop
publication. FEASIBLE is not counted as OPT. No GA comparison is included.
''')
    figures(output,checked,instances)
    return counts


def verify_cache(output, identity):
    manifest=json.loads((output/'sources.json').read_text())
    if manifest['identity'] != identity:
        raise ValueError('report fingerprint collision or mismatched manifest')
    hashes=manifest['outputs_sha256']
    if {p.name for p in output.iterdir()} != set(hashes)|{'sources.json'}:
        raise ValueError('report contains missing or unexpected files; use a new output root')
    if any(digest(output/name)!=value for name,value in hashes.items()):
        raise ValueError('generated report was edited; refusing to overwrite it')
    return manifest['counts']


def publish(input_path, output_root):
    import matplotlib
    import numpy
    checked,instances,summary,meta=audit(input_path)
    inputs=[input_path,input_path.with_suffix('.metadata.json'),input_path.with_suffix('.witnesses.jsonl')]
    sources=[Path(__file__).resolve(),ROOT/'scripts/audit_general_pilot.py',ROOT/'benchmarks/general_suite.py',
             ROOT/'src/core/graph_utils.py',ROOT/'src/core/parameters.py']
    identity=dict(inputs={str(p.relative_to(ROOT)):digest(p) for p in inputs},
                  sources={str(p.relative_to(ROOT)):digest(p) for p in sources},
                  environment=dict(python=sys.version,networkx=nx.__version__,matplotlib=matplotlib.__version__,numpy=numpy.__version__))
    version=hashlib.sha256(json.dumps(identity,sort_keys=True).encode()).hexdigest()[:16]
    output=output_root/version
    output_root.mkdir(parents=True,exist_ok=True)
    if output.exists():
        counts=verify_cache(output,identity)
        print(f'Reused verified report: {output.relative_to(ROOT)}',flush=True)
    else:
        temp=Path(tempfile.mkdtemp(prefix='.building-',dir=output_root))
        try:
            counts=artifacts(temp,checked,instances,summary)
            manifest=dict(identity=identity,counts=counts,original_manifest=meta,
                          outputs_sha256={p.name:digest(p) for p in temp.iterdir()})
            (temp/'sources.json').write_text(json.dumps(manifest,indent=2)+'\n')
            temp.rename(output)
        except BaseException:
            shutil.rmtree(temp)
            raise
        print(f'Created report: {output.relative_to(ROOT)}',flush=True)
    relative=output.relative_to(ROOT).as_posix()
    wrapper=ROOT/'paper/generated/general_confirm.tex'
    wrapper.parent.mkdir(parents=True,exist_ok=True)
    text=(f'% Generated by scripts/build_confirmation_report.py\n'
          f'\\input{{{relative}/counts.tex}}\n'
          f'\\newcommand{{\\ConfirmReportDir}}{{{relative}}}\n')
    if not wrapper.exists() or wrapper.read_text()!=text:
        wrapper.write_text(text)
    print(f"Validated {len(checked)} witnesses; SAT {counts['ConfirmSATOpt']}/351 OPT, ILP {counts['ConfirmILPOpt']}/351 OPT",flush=True)
    return output,counts


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only',action='store_true')
    args=parser.parse_args()
    path=ROOT/'results/runs/general_confirm_r1.csv'
    if args.check_only:
        checked,_,_,_=audit(path)
        print(f'Validated {len(checked)} observations; no files written')
    else:
        publish(path,ROOT/'results/analysis/general_confirm_r1')
