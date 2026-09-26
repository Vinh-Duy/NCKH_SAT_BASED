"""Summarize a current paired run by family, keeping unresolved instances visible."""

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import statistics


def read_run(path):
    with Path(path).open(newline='', encoding='utf-8') as source:
        rows = list(csv.DictReader(source))
    required = {'Graph', 'Family', 'lambda_Base', 'lambda_Sym', 'Status_Base', 'Status_Sym',
                'Time_Base', 'Time_Sym', 'Count_Span', 'Count_Span_Kind', 'Symmetry_Rule',
                'Clause_Base', 'Clause_Sym', 'Consistent'}
    if not rows or not required.issubset(rows[0]):
        raise ValueError('Use a current comparison CSV, not a sizes-only or legacy CSV.')
    seen = set()
    for row in rows:
        if None in row or any(value is None for value in row.values()):
            raise ValueError('incomplete CSV row; do not summarize a partially written result')
        name = row['Graph']
        if name in seen:
            raise ValueError(f'duplicate graph: {name}')
        seen.add(name)
        match = re.fullmatch(r'([CP])_\d+([xo])([CP])_\d+', name)
        family = ''.join(match.groups()) if match else 'C' if re.fullmatch(r'C_\d+', name) else None
        if family is None or row['Family'] != family:
            raise ValueError(f'family mismatch: {name}')
        for suffix in ('Base', 'Sym'):
            if row[f'Status_{suffix}'] not in {'OPT', 'FEASIBLE'}:
                raise ValueError(f'unexpected SAT status: {name}')
            for metric in ('lambda', 'Clause'):
                row[f'{metric}_{suffix}'] = int(row[f'{metric}_{suffix}'])
                if row[f'{metric}_{suffix}'] < 0:
                    raise ValueError(f'negative {metric}: {name}')
            value = float(row[f'Time_{suffix}'])
            if not math.isfinite(value) or value < 0:
                raise ValueError(f'invalid runtime: {name}')
            row[f'Time_{suffix}'] = value
        paired = row['Status_Base'] == row['Status_Sym'] == 'OPT'
        if paired and row['lambda_Base'] != row['lambda_Sym']:
            raise ValueError(f'optimal spans disagree: {name}')
        if int(row['Count_Span']) != max(row['lambda_Base'], row['lambda_Sym']):
            raise ValueError(f'count span does not match the declared common bound: {name}')
        if row['Count_Span_Kind'] != ('OPT' if paired else 'FEASIBLE_UB'):
            raise ValueError(f'count span classification mismatch: {name}')
        if row['Consistent'] != ('YES' if paired else 'UNPROVEN'):
            raise ValueError(f'consistency classification mismatch: {name}')
    return rows


def summarize(rows):
    result = []
    for family in sorted({r['Family'] for r in rows}):
        group = [r for r in rows if r['Family'] == family]
        paired = [r for r in group if r['Status_Base'] == r['Status_Sym'] == 'OPT']
        ratios = [r['Time_Base'] / r['Time_Sym'] for r in paired if r['Time_Sym'] > 0]
        reductions = [100 * (1 - r['Clause_Sym'] / r['Clause_Base'])
                      for r in paired if r['Clause_Base'] > 0]
        result.append({
            'Family': family, 'Rows': len(group), 'Paired_OPT': len(paired),
            'Unresolved_Pairs': len(group) - len(paired),
            'Base_FEASIBLE': sum(r['Status_Base'] == 'FEASIBLE' for r in group),
            'Sym_FEASIBLE': sum(r['Status_Sym'] == 'FEASIBLE' for r in group),
            'Symmetry_Rules': ','.join(sorted({r['Symmetry_Rule'] for r in group})),
            'Paired_Time_Base': sum(r['Time_Base'] for r in paired),
            'Paired_Time_Sym': sum(r['Time_Sym'] for r in paired),
            'Median_Paired_Speedup': statistics.median(ratios) if ratios else None,
            'Median_Paired_Clause_Reduction_Pct': statistics.median(reductions) if reductions else None,
        })
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    try:
        rows = read_run(args.input)
        summary = summarize(rows)
    except (ValueError, KeyError) as error:
        parser.error(str(error))
    args.output_dir.mkdir(parents=True, exist_ok=False)
    with (args.output_dir / 'summary.csv').open('x', newline='', encoding='utf-8') as target:
        writer = csv.DictWriter(target, fieldnames=list(summary[0]))
        writer.writeheader()
        writer.writerows(summary)
    provenance = {'input': str(args.input.resolve()),
                  'input_sha256': hashlib.sha256(args.input.read_bytes()).hexdigest(),
                  'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    metadata = args.input.with_suffix('.metadata.json')
    if metadata.exists():
        provenance['run_manifest'] = json.loads(metadata.read_text())
    (args.output_dir / 'source.json').write_text(json.dumps(provenance, indent=2) + '\n')
    lines = ['# Paired symmetry experiment summary', '',
             'Times and clause reductions below use only pairs with both OPT and equal spans.',
             'Unresolved pairs are counted separately; excluding them from timings can favor easy instances.',
             'A rule of `none` is a repeat of the same model, not evidence of a symmetry benefit.',
             'This is a descriptive single-run summary, not a significance test.', '',
             '| Family | Rows | Paired OPT | Unresolved | Rules | Median time Base/Sym |',
             '|---|---:|---:|---:|---|---:|']
    for row in summary:
        ratio = row['Median_Paired_Speedup']
        ratio = f'{ratio:.3f}' if ratio is not None else '—'
        lines.append(f"| {row['Family']} | {row['Rows']} | {row['Paired_OPT']} | "
                     f"{row['Unresolved_Pairs']} | {row['Symmetry_Rules']} | {ratio} |")
    (args.output_dir / 'summary.md').write_text('\n'.join(lines) + '\n')
    print(f'Saved {len(summary)} family summaries to {args.output_dir}')


if __name__ == '__main__':
    main()
