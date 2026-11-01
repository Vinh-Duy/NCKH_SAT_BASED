# Phase 3E.2 IPASIR-UP perturbation pilot

Run sequentially with `.venv-1/bin/python -m experiments.phase3e2_ipasir_up_pilot.runner`.

This isolated diagnostic pilot uses only ER-60, `(h,k)=(3,2)`, `U=112`, Reference/Threshold formulas, fresh worker processes, and modes A-D. Mode A is uninstrumented; B connects a no-op propagator without observations; C/D observe deterministic 1%/5% semantic samples. It is not production telemetry and must not be merged with canonical Phase 3E performance results.
