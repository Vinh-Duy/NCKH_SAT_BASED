# Phase 3D threshold prototype

This package is an isolated, pure-Python experiment. It is not connected to
production SAT paths and does not import or initialize a SAT backend.

From the repository root:

```sh
python3 experiments/phase3d_threshold_encoding/run_experiment.py
python3 -m unittest discover -s experiments/phase3d_threshold_encoding/tests
```

The experiment builds one formula at a time for the exact ER-60
`p=0.30, seed=100` graph at `U=112` and `U=127`. It performs independent
arithmetic and exhaustive small-graph checks only.
