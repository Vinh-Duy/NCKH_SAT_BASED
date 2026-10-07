"""Run the fixed v2 confirmation, then audit and summarize it automatically."""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.core.io import default_output
from scripts.summarize_progress_run import export


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan-only', action='store_true')
    parser.add_argument('--resume', type=Path, help='incomplete v2 CSV, with unchanged source/environment')
    args = parser.parse_args()
    path = args.resume.resolve() if args.resume else default_output('general_progress_v2')
    command = [sys.executable, str(ROOT/'benchmarks/benchmark_sat_vs_ilp.py'),
               '--suite', 'general-pilot-v1', '--pairs', '1,1', '2,1', '3,2',
               '--methods', 'cadical', 'gurobi', '--repeats', '3', '--timeout', '30',
               '--output', str(path)]
    if args.resume:
        command.append('--resume')
    if args.plan_only:
        command.append('--plan-only')
    print(f'Output: {path}', flush=True)
    subprocess.run(command, cwd=ROOT, check=True)
    if not args.plan_only:
        output = export(path, ROOT/'results/analysis/progress_confirmation')
        print(f'Validated report: {output}', flush=True)
        print('Review summary.csv and paired_bounds.csv before updating the manuscript.')


if __name__ == '__main__':
    main()
