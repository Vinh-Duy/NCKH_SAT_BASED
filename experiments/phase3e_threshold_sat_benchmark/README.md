# Phase 3E SAT benchmark runner

This package is isolated from production SAT paths. It imports only the
Phase 3D pure-Python formula builders and initializes CaDiCaL195 inside fresh
worker processes for the exact authorized workload.

Run from the repository root:

```sh
.venv-1/bin/python -m experiments.phase3e_threshold_sat_benchmark.runner
```

The runner performs formula preflight, then executes twelve sequential runs:
three reference and three threshold runs at each of `U=112` and `U=127`.
