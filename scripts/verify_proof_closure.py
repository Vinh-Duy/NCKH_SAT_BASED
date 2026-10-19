"""Reconstruct and independently verify the complete v2 optimality package.

Only Python's standard library is needed, including for the graph-to-CNF
reconstruction and LRAT replay. No stored OPT flag or floating-point objective
is accepted as lower-bound evidence. Runtime comparisons remain unchanged.
"""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.capacity_bound_certificate import verify as verify_capacity
from scripts.certificate_support import mathematical_support
from scripts.lrat_checker import verify_file as verify_lrat
from scripts.verify_clique_certificate import verify as verify_witness
from src.models.certificate_encoding import build_order_formula
from src.models.color_rank_encoding import build_color_rank_cnf

BASE = ROOT / 'results/analysis/color_order/2d62af353a1756ae'
DEFAULT = ROOT / 'results/analysis/proof_closure/v1_20261018'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def records(path):
    values = [json.loads(line) for line in Path(path).read_text().splitlines()]
    by_id = {c['id']: c for c in values}
    if len(by_id) != len(values) or not values:
        raise ValueError('empty records or duplicate IDs')
    return by_id


def csv_text(rows):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def audit(directory=DEFAULT, baseline=BASE, progress=False):
    directory, baseline = Path(directory), Path(baseline)
    old = records(baseline / 'certificates.jsonl')
    witnesses = records(directory / 'witnesses.jsonl')
    capacities = records(directory / 'capacity_certificates.jsonl')
    with (baseline / 'instances.csv').open(newline='') as stream:
        previous = {r['Certificate_ID']: r for r in csv.DictReader(stream)}
    if set(old) != set(witnesses) or set(old) != set(previous) or len(old) != 117:
        raise ValueError('the bundle must cover exactly the original 117 instances')
    for key, witness in witnesses.items():
        original = old[key]
        if any(witness[field] != original[field] for field in ('graph', 'graph_sha256', 'h', 'k', 'instance')):
            raise ValueError('witness changes the original instance')
        verify_witness(witness)
        if witness['upper_bound'] > original['upper_bound']:
            raise ValueError('a better original witness was discarded')
    bounds = {}
    for key, certificate in capacities.items():
        if key not in old or any(certificate[field] != old[key][field]
                                for field in ('graph', 'graph_sha256', 'h', 'k', 'instance')):
            raise ValueError('capacity certificate targets a different instance')
        bounds[key] = verify_capacity(certificate)['lower_bound']
    proof_bounds, checks = {}, []
    for proof in json.loads((directory / 'proofs.json').read_text()):
        key = proof['id']
        if key not in old or key in proof_bounds:
            raise ValueError('unknown or duplicated proof ID')
        certificate = old[key]
        if any(proof[field] != certificate[field] for field in ('graph_sha256', 'h', 'k')):
            raise ValueError('proof parameters differ from the original instance')
        path = (directory / proof['proof']).resolve()
        if not path.is_relative_to(directory.resolve()) or digest(path) != proof['sha256']:
            raise ValueError('proof path or hash mismatch')
        if proof['format'] != 'lrat-rup':
            raise ValueError('unsupported proof format')
        span = proof['span']
        if type(span) is not int or span < 0:
            raise ValueError('proof span must be a nonnegative integer')
        if proof['encoding'] == 'color-rank':
            formula, _ = build_color_rank_cnf(certificate['graph'], span,
                proof['h'], proof['k'], proof['clique'], proof['reflection_root'])
        elif proof['encoding'] == 'order':
            formula = build_order_formula(certificate['graph'], span, proof['h'], proof['k'])
        else:
            raise ValueError('unrecognized graph-to-CNF encoding')
        check = verify_lrat(formula, path)
        checks.append(dict(id=key, **check))
        proof_bounds[key] = span + 1
        if progress:
            print(f'Checked {key}: UNSAT at {span}', flush=True)
    rows = []
    for key, certificate in witnesses.items():
        math = mathematical_support(certificate)
        low = max(math['Mathematical_LB'], bounds.get(key, 0), proof_bounds.get(key, 0))
        high = certificate['upper_bound']
        if low > high:
            raise ValueError('independent lower bound contradicts a valid labeling')
        kind = ('theory/clique' if math['Mathematical_LB'] == high else
                'capacity' if bounds.get(key) == high else
                'UNSAT proof' if proof_bounds.get(key) == high else 'open')
        before = previous[key]
        rows.append(dict(Certificate_ID=key, Instance=certificate['instance'], Group=before['Group'],
            h=certificate['h'], k=certificate['k'], V=certificate['graph']['n'],
            Before_LB=int(before['Final_LB']), Before_UB=int(before['Final_UB']),
            Mathematical_LB=math['Mathematical_LB'], Capacity_LB=bounds.get(key, ''),
            UNSAT_LB=proof_bounds.get(key, ''), Final_LB=low, Final_UB=high,
            Evidence=kind, Independently_Closed=low == high,
            Newly_Closed=int(before['Final_LB']) < int(before['Final_UB']) and low == high,
            Improved_UB=high < int(before['Final_UB']), Witness_Source=certificate.get('source_kind', 'archived_v2')))
    counts = dict(instances=len(rows), independently_closed=sum(r['Independently_Closed'] for r in rows),
                  open=sum(not r['Independently_Closed'] for r in rows),
                  newly_closed=sum(r['Newly_Closed'] for r in rows),
                  improved_upper_bounds=sum(r['Improved_UB'] for r in rows),
                  theory_clique=sum(r['Evidence'] == 'theory/clique' for r in rows),
                  capacity=sum(r['Evidence'] == 'capacity' for r in rows),
                  unsat=sum(r['Evidence'] == 'UNSAT proof' for r in rows))
    return rows, counts, checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, default=DEFAULT)
    parser.add_argument('--write', action='store_true', help='write derived tables after full verification')
    args = parser.parse_args()
    start = time.monotonic()
    directory = args.directory
    manifest_path = directory / 'sources.json'
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        for name, expected in manifest['inputs'].items():
            if digest(ROOT / name) != expected:
                raise ValueError(f'input hash mismatch: {name}')
        for name, expected in manifest['artifacts'].items():
            if digest(directory / name) != expected:
                raise ValueError(f'artifact hash mismatch: {name}')
    rows, counts, checks = audit(directory, progress=True)
    if counts['independently_closed'] != 117:
        raise ValueError('this complete-closure package still contains an open instance')
    selected = [r for r in rows if r['Before_LB'] < r['Before_UB']]
    outputs = {'instances.csv': csv_text(rows), 'originally_open.csv': csv_text(selected),
               'summary.json': json.dumps(counts, indent=2) + '\n',
               'proof_checks.json': json.dumps(checks, indent=2) + '\n'}
    six = sorted({r['Instance'] for r in selected})
    lines = [r'\begin{tabular}{lrrr}', r'\toprule',
             r'Graph & $\lambda_{1,1}$ & $\lambda_{2,1}$ & $\lambda_{3,2}$ \\', r'\midrule']
    for name in six:
        group = sorted((r for r in rows if r['Instance'] == name), key=lambda r: r['h'])
        lines.append(name.replace('_', r'\_') + ' & ' + ' & '.join(str(r['Final_UB']) for r in group) + r' \\')
    lines += [r'\bottomrule', r'\end{tabular}', '']
    outputs['six_graphs.tex'] = '\n'.join(lines)
    lines = [r'\begin{tabular}{llrrrrr}', r'\toprule',
             r'Family & $(h,k)$ & Cases & Before & Added & Certified & Open \\', r'\midrule']
    for group, h, k in sorted({(r['Group'], r['h'], r['k']) for r in rows}):
        subset = [r for r in rows if (r['Group'], r['h'], r['k']) == (group, h, k)]
        before = sum(r['Before_LB'] == r['Before_UB'] for r in subset)
        added = sum(r['Newly_Closed'] for r in subset)
        closed = sum(r['Independently_Closed'] for r in subset)
        lines.append(f'{group} & ({h},{k}) & {len(subset)} & {before} & {added} & {closed} & {len(subset)-closed}' + r' \\')
    lines += [r'\midrule', r'All & -- & 117 & 101 & 16 & 117 & 0 \\', r'\bottomrule', r'\end{tabular}', '']
    outputs['summary.tex'] = '\n'.join(lines)
    for name, text in outputs.items():
        if args.write:
            (directory / name).write_text(text)
        elif not (directory / name).exists() or (directory / name).read_text() != text:
            raise ValueError(f'derived table differs from replay: {name}')
    if args.write:
        inputs = {str(p.relative_to(ROOT)): digest(p) for p in
                  (BASE / 'certificates.jsonl', BASE / 'instances.csv')}
        artifacts = {str(p.relative_to(directory)): digest(p) for p in sorted(directory.rglob('*'))
                     if p.is_file() and p.name not in {'sources.json', 'README.md'}}
        sources = [Path(__file__), ROOT/'scripts/capacity_bound_certificate.py',
                   ROOT/'scripts/lrat_checker.py', ROOT/'scripts/rup_checker.py',
                   ROOT/'src/models/color_rank_encoding.py', ROOT/'src/models/certificate_encoding.py']
        manifest_path.write_text(json.dumps(dict(kind='posthoc-proof-closure-v1',
            inputs=inputs, artifacts=artifacts,
            verification_sources={str(p.relative_to(ROOT)): digest(p) for p in sources}), indent=2) + '\n')
    print(json.dumps(counts, sort_keys=True))
    print(f'Independent replay completed in {time.monotonic() - start:.2f}s.')


if __name__ == '__main__':
    main()
