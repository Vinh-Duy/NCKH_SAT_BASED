# Conflict budget boundary policy

The installed CaDiCaL195 backend can exceed a configured `conf_budget`; the
controlled matrix observed deltas of 3 for a budget of 2, 11 for 10, 21 for
20, and 53 for 50. The excess was therefore not reliably bounded by one
conflict.

The implementation uses a one-conflict guard band: for task budget `B` and
remaining budget `R`, it configures `R - 1` when `R > 1` and makes no further
call when `R <= 1`. It records the actual cumulative counter delta without
clipping it, including `budget_overrun` and `budget_accounting_valid`.

This policy kept the tested guarded synthetic calls at or below their task
budgets, but it does not establish a universal strict cap: the original
ER-60 recalibration arm configured 9,999 and observed 10,001 conflicts. The
policy must therefore be treated as a conservative soft-threshold policy,
not as a strict resource guarantee, until a backend/API with enforceable
hard accounting is used.
