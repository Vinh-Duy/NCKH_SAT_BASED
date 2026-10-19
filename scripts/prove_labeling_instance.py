"""Reproduce a supplementary fixed-span decision in a fresh output directory.

This is a proof experiment, not the original timed SAT/ILP benchmark.
Pass --drat-trim to check UNSAT and export a standalone-checkable LRAT file.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.models.certificate_encoding import build_order_formula
from src.models.color_rank_encoding import build_color_rank_cnf, decode
from scripts.lrat_checker import verify_file
from scripts.verify_clique_certificate import verify as verify_labeling


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--id', required=True, help='full Certificate_ID from the proof package')
    parser.add_argument('--span', required=True, type=int)
    parser.add_argument('--encoding', choices=['order', 'color-rank'], default='color-rank')
    parser.add_argument('--timeout', type=float, default=120)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--drat-trim', type=Path)
    args = parser.parse_args()
    if not 0 < args.timeout < float('inf'):
        parser.error('--timeout must be positive and finite')
    from pysat.solvers import Glucose4

    source = ROOT/'results/analysis/proof_closure/v1_20261018/witnesses.jsonl'
    matches = [c for c in map(json.loads, source.read_text().splitlines()) if c['id'] == args.id]
    if len(matches) != 1:
        parser.error('unknown or duplicated certificate ID')
    certificate = matches[0]
    graph = certificate['graph']
    degrees = [0] * graph['n']
    for u, v in graph['edges']:
        degrees[u] += 1
        degrees[v] += 1
    root = max(range(graph['n']), key=lambda v: degrees[v]) if certificate['k'] == 2 else None
    start = time.monotonic()
    if args.encoding == 'color-rank':
        formula, layout = build_color_rank_cnf(graph, args.span, certificate['h'], certificate['k'],
                                              certificate['clique'], root)
    else:
        formula = build_order_formula(graph, args.span, certificate['h'], certificate['k'])
    args.output.mkdir(parents=True, exist_ok=False)
    nvars = max((abs(lit) for clause in formula for lit in clause), default=0)
    dimacs = f'p cnf {nvars} {len(formula)}\n' + ''.join(' '.join(map(str, c)) + ' 0\n' for c in formula)
    (args.output/'formula.cnf').write_text(dimacs)
    metadata = dict(id=args.id, graph=graph, graph_sha256=certificate['graph_sha256'],
                    h=certificate['h'], k=certificate['k'], span=args.span,
                    encoding=args.encoding, clique=certificate['clique'], reflection_root=root,
                    solver='Glucose4', solver_timeout_seconds=args.timeout,
                    cnf_sha256=hashlib.sha256(dimacs.encode()).hexdigest())
    (args.output/'protocol.json').write_text(json.dumps(metadata, indent=2) + '\n')
    with Glucose4(bootstrap_with=formula, with_proof=True) as solver:
        timer = threading.Timer(args.timeout, solver.interrupt)
        timer.start()
        try:
            outcome = solver.solve_limited(expect_interrupt=True)
        finally:
            timer.cancel()
        result = dict(status='UNKNOWN' if outcome is None else 'SAT' if outcome else 'UNSAT',
                      elapsed_seconds=time.monotonic() - start, stats=solver.accum_stats())
        if outcome:
            model = solver.get_model()
            if args.encoding == 'color-rank':
                labels = decode(model, layout)
            else:
                positive = set(model)
                labels = [next((t for t in range(args.span) if 1 + v * args.span + t in positive), args.span)
                          for v in range(graph['n'])]
            checked = dict(certificate, labels=labels, upper_bound=max(labels) - min(labels))
            verify_labeling(checked)
            result['labels'] = labels
        elif outcome is False:
            rup = ('\n'.join(solver.get_proof()) + '\n').encode('ascii')
            (args.output/'proof.rup.gz').write_bytes(gzip.compress(rup, mtime=0))
            result['independently_verified'] = False
            if args.drat_trim:
                (args.output/'proof.rup').write_bytes(rup)
                run = subprocess.run([str(args.drat_trim.resolve()), str(args.output/'formula.cnf'),
                                      str(args.output/'proof.rup'), '-p', '-U', '-L',
                                      str(args.output/'proof.lrat')], capture_output=True, text=True, check=True)
                if 's VERIFIED' not in run.stdout:
                    raise RuntimeError('DRAT-trim did not report verification')
                (args.output/'drat-trim.log').write_text(run.stdout + run.stderr)
                result['proof_check'] = verify_file(formula, args.output/'proof.lrat')
                result['independently_verified'] = True
                (args.output/'proof.lrat.gz').write_bytes(gzip.compress((args.output/'proof.lrat').read_bytes(), mtime=0))
                (args.output/'proof.rup').unlink()
                (args.output/'proof.lrat').unlink()
    (args.output/'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
