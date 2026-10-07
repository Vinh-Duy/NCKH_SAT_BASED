"""Verify the frozen v1 report after benchmark development continues.

This checks recorded inputs/outputs and manifest identity; it does not rerun the
v1 source-protocol audit. Reconstructing that audit still needs its old checkout.
"""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.build_confirmation_report import digest, verify_cache


def verify(output, root=ROOT):
    manifest = json.loads((output/'sources.json').read_text())
    identity = manifest['identity']
    version = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:16]
    if output.name != version:
        raise ValueError('archived report identity does not match its version')
    for name, expected in identity['inputs'].items():
        if digest(root/name) != expected:
            raise ValueError(f'archived input changed: {name}')
    return verify_cache(output, identity)


if __name__ == '__main__':
    output = ROOT/'results/analysis/unresolved_bounds/9305340bdfd63009'
    verify(output)
    wrapper = ROOT/'paper/generated/unresolved_bounds.tex'
    relative = output.relative_to(ROOT).as_posix()
    expected = f'\\input{{{relative}/counts.tex}}\n\\newcommand{{\\BoundsReportDir}}{{{relative}}}\n'
    if wrapper.read_text() != expected:
        raise ValueError('manuscript pointer differs from the frozen report')
    print(f'Verified frozen v1 report inputs and outputs: {output.relative_to(ROOT)}')
