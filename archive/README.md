# Archives outside the current pipeline

- `code/`: the original `archive_old_code/` and three historical scripts formerly at the repository root (`validation.py`, `visual.py`, `plot_results.py`). Their old internal imports are colocated here; the maintained API is `src/` and the CLI is `benchmarks/`.
- `logs/`: historical logs formerly stored in the root `logs/` directory.
- `reports/legacy_root/`: the old PDF and LaTeX auxiliary files formerly next to main.tex.
- `cache/`: old compilation caches, ignored by Git.

Historical executable code, logs, and report binaries are retained as provenance records, including paths embedded in them. They are not the tools for reproducing current experiments. The current PDF is [build/main.pdf](../build/main.pdf).

Historical research data are in [results/archive/](../results/archive/). Repository documentation is presented in English; immutable historical artifacts may retain their original language.

[English historical-code reading copies](translations/README.md) are available separately from the preserved executables.
