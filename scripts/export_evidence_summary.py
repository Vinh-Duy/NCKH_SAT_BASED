"""Consolidate the 117-instance evidence without pooling v1/v2 observations.

Baseline and final columns use the completed v2 run. The archived v1
classification is checked separately, never used to tighten v2 intervals.
"""
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
from scripts.analyze_clique_certificates import DEFAULT_INPUT
from scripts.analyze_confirmation_gaps import analyze
from scripts.build_confirmation_report import digest, verify_cache, write_csv
from scripts.summarize_progress_run import collect
from scripts.verify_clique_certificate import verify_file

CLIQUE = ROOT/'results/analysis/clique_certificates/cc0e412739ccc8d2'
ARCHIVED = ROOT/'results/analysis/confirmation_gaps/3bec94390952fd50'


def read_rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def keyed(rows):
    result = {}
    for row in rows:
        key = row['Instance'], int(row['h']), int(row['k'])
        if key in result:
            raise ValueError('duplicate instance; repetitions must not be counted as instances')
        result[key] = row
    return result


def consolidate(baseline, archived, clique_rows, proofs):
    current, old, cliques = map(keyed, (baseline, archived, clique_rows))
    if not current or not current.keys() == old.keys() == cliques.keys():
        raise ValueError('cohort mismatch between archived, current, and clique reports')
    if set(proofs) != {r['Certificate_ID'] for r in cliques.values()} or len(proofs) != len(current):
        raise ValueError('certificate coverage mismatch')
    instances = []
    for key, row in sorted(current.items()):
        previous, clique = old[key], cliques[key]
        if any((r['Group'], int(r['V'])) != (row['Group'], int(row['V'])) for r in (previous, clique)):
            raise ValueError('instance group or graph order mismatch')
        low, upper = int(row['Combined_LB']), int(row['Best_Witness_UB'])
        if (low, upper) != (int(clique['Original_LB']), int(clique['Witness_UB'])):
            raise ValueError('clique report does not match the current v2 interval')
        proof = proofs[clique['Certificate_ID']]
        if (proof['lower_bound'], proof['upper_bound']) != (int(clique['Clique_LB']), upper):
            raise ValueError('certificate bound mismatch')
        final_lb = max(low, proof['lower_bound'])
        if final_lb > upper or final_lb != int(clique['Augmented_LB']):
            raise ValueError('invalid augmented interval')
        evidence = row['Evidence']
        if evidence not in {'THEORY_MATCH', 'RECORDED_OPT', 'COMBINED_CLOSURE', 'OPEN'}:
            raise ValueError('unknown baseline evidence category')
        if (evidence == 'OPEN') != (low < upper):
            raise ValueError('baseline category contradicts interval')
        instances.append(dict(Instance=key[0], Group=row['Group'], h=key[1], k=key[2],
            V=int(row['V']), V1_Evidence=previous['Evidence'], V2_Evidence=evidence,
            Theory=int(evidence == 'THEORY_MATCH'),
            Other_Closed=int(evidence in {'RECORDED_OPT', 'COMBINED_CLOSURE'}),
            Open_Before=int(low < upper), Clique_Certified=int(proof['optimal']),
            Newly_Closed=int(low < upper and final_lb == upper),
            Closed_After=int(final_lb == upper), Open_After=int(final_lb < upper),
            Baseline_LB=low, Witness_UB=upper, Clique_LB=proof['lower_bound'], Final_LB=final_lb,
            Certificate_ID=clique['Certificate_ID']))
    fields = ('Theory', 'Other_Closed', 'Open_Before', 'Clique_Certified',
              'Newly_Closed', 'Closed_After', 'Open_After')
    summary = []
    for group, h, k in sorted({(r['Group'], r['h'], r['k']) for r in instances}):
        selected = [r for r in instances if (r['Group'], r['h'], r['k']) == (group, h, k)]
        summary.append(dict(Group=group, h=h, k=k, Instances=len(selected),
                            **{field: sum(r[field] for r in selected) for field in fields}))
    summary.append(dict(Group='ALL', h='', k='', Instances=len(instances),
                        **{field: sum(r[field] for r in instances) for field in fields}))
    for row in summary:
        if not (row['Theory']+row['Other_Closed']+row['Open_Before'] == row['Instances']
                and row['Closed_After']+row['Open_After'] == row['Instances']
                and row['Theory']+row['Other_Closed']+row['Newly_Closed'] == row['Closed_After']
                and row['Newly_Closed'] <= row['Clique_Certified'] <= row['Closed_After']):
            raise ValueError('summary partitions or overlapping certificate counts are invalid')
    return instances, summary


def verified_manifest(directory):
    manifest = json.loads((directory/'sources.json').read_text())
    verify_cache(directory, manifest['identity'])
    for name, expected in manifest['identity']['inputs'].items():
        if digest(ROOT/name) != expected:
            raise ValueError('archived raw input fingerprint mismatch')
    return manifest


def export(output_root):
    checked, *_ = collect(DEFAULT_INPUT)
    baseline, *_ = analyze(checked)
    clique_manifest = verified_manifest(CLIQUE)
    verified_manifest(ARCHIVED)
    for path in (DEFAULT_INPUT, DEFAULT_INPUT.with_suffix('.metadata.json'), DEFAULT_INPUT.with_suffix('.witnesses.jsonl')):
        if clique_manifest['identity']['inputs'].get(str(path.relative_to(ROOT))) != digest(path):
            raise ValueError('clique certificates belong to a different run')
    instances, summary = consolidate(baseline, read_rows(ARCHIVED/'instances.csv'),
                                    read_rows(CLIQUE/'instances.csv'), verify_file(CLIQUE/'certificates.jsonl'))
    sources = [Path(__file__).resolve(), ROOT/'scripts/analyze_confirmation_gaps.py',
               ROOT/'scripts/summarize_progress_run.py', ROOT/'scripts/build_confirmation_report.py',
               ROOT/'scripts/audit_general_pilot.py', ROOT/'scripts/compare_unresolved_bounds.py',
               ROOT/'scripts/verify_clique_certificate.py', *ROOT.glob('src/**/*.py'), *ROOT.glob('benchmarks/*.py')]
    identity = dict(kind='consolidated-v2-evidence-v1',
                    reports={str(p.relative_to(ROOT)): digest(p) for p in
                             (CLIQUE/'sources.json', ARCHIVED/'sources.json')},
                    sources={str(p.relative_to(ROOT)): digest(p) for p in sorted(set(sources))})
    version = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16]
    output_root.mkdir(parents=True, exist_ok=True)
    output = output_root/version
    if output.exists():
        verify_cache(output, identity)
        return output
    temporary = Path(tempfile.mkdtemp(prefix='.building-', dir=output_root))
    try:
        write_csv(temporary/'instances.csv', instances)
        write_csv(temporary/'summary.csv', summary)
        total = summary[-1]
        counts = {f'Evidence{key.replace("_", "")}': value for key, value in total.items()
                  if key not in {'Group', 'h', 'k'}}
        counts['EvidenceVOneSame'] = sum(r['V1_Evidence'] == r['V2_Evidence'] for r in instances)
        (temporary/'counts.tex').write_text(''.join(f'\\newcommand{{\\{key}}}{{{value}}}\n' for key, value in counts.items()))
        lines = [r'\begin{tabular}{@{}llrrrrrrr@{}}', r'\toprule',
                 r'& & & \multicolumn{3}{c}{Before clique (v2)} & \multicolumn{3}{c}{After adding clique}\\',
                 r'\cmidrule(lr){4-6}\cmidrule(l){7-9}',
                 r'Family & $(h,k)$ & Cases & Theory & Other & Open & Clique-cert. & Closed & Open\\', r'\midrule']
        for row in summary:
            if row['Group'] == 'ALL':
                lines.append(r'\midrule')
            family = {'tree': 'Tree', 'PxP': r'$P_n\square P_m$', 'ALL': 'Total'}.get(row['Group'], row['Group'])
            pair = '--' if row['Group'] == 'ALL' else f"$({row['h']},{row['k']})$"
            lines.append(' & '.join([family, pair, *[str(row[key]) for key in
                ('Instances', 'Theory', 'Other_Closed', 'Open_Before', 'Clique_Certified', 'Closed_After', 'Open_After')]])+r'\\')
        (temporary/'summary.tex').write_text('\n'.join([*lines, r'\bottomrule', r'\end{tabular}'])+'\n')
        (temporary/'README.md').write_text('''# Consolidated evidence for the confirmation cohort

One row per family and (h,k), followed by a total; all 117 distinct instances are included.
This is a presentation/aggregation of existing evidence, not another experiment.

- `instances.csv`: exact join by Instance/h/k of audited v2 intervals, archived v1 categories,
  and independently checked clique certificates. Repeats are not additional instances.
- `summary.csv`: 15 group/parameter rows and one ALL row. Do not sum ALL with group rows.
- `summary.tex`, `counts.tex`: manuscript table and counts derived from these records.
- `sources.json`: input-report and analysis-source fingerprints; output hashes protect cached artifacts.

Before-clique columns use only the complete v2 run: Theory means a witness attains the
applicable pre-clique theoretical lower bound; Other_Closed means another closed interval;
Open_Before means unequal bounds. These three columns partition Instances.
Clique_Certified means the square-clique bound alone equals the validated witness span.
It overlaps earlier closed cases and must NOT be added to Theory or Other_Closed.
Newly_Closed counts only previously open cases certified by the added bound.
Closed_After + Open_After = Instances; Closed_After = Theory + Other_Closed + Newly_Closed.

The total is 61 theory matches + 35 other closures + 21 open before clique; 50 clique-certified
cases include only 2 newly closed cases. After adding clique evidence, 98 are closed and 19 open.
The archived v1 categories agree with v2 for all 117 instances, but interval widths,
observations, timing and native progress differ. V1 evidence is NOT pooled into v2 intervals.
V1_Evidence is retained only for a traceable historical comparison.

Raw statuses and timed solver coverage are unchanged. Saved solver lower bounds remain
trusted claims wherever a matching independent mathematical bound is unavailable.
''')
        (temporary/'sources.json').write_text(json.dumps(dict(identity=identity, counts=counts,
            outputs_sha256={p.name: digest(p) for p in temporary.iterdir()}), indent=2)+'\n')
        temporary.rename(output)
    except BaseException:
        shutil.rmtree(temporary)
        raise
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root', type=Path, default=ROOT/'results/analysis/evidence_summary')
    args = parser.parse_args()
    output = export(args.output_root)
    relative = output.resolve().relative_to(ROOT).as_posix()
    (ROOT/'paper/generated/evidence_summary.tex').write_text(
        '% Generated by scripts/export_evidence_summary.py\n'
        f'\\input{{{relative}/counts.tex}}\n'
        f'\\newcommand{{\\EvidenceReportDir}}{{{relative}}}\n')
    print(output)
