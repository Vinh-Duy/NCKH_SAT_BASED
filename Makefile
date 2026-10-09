PYTHON ?= .venv-1/bin/python
LATEXMK ?= /Library/TeX/texbin/latexmk

.PHONY: test report tables figures pdf tree-tables manuscript paper-figures confirmation confirmation-data progress-data clique-data english-tables gap-data gap-analysis bounds-data bounds-verify bounds-comparison

# Audit completed confirmation data, publish tables/figures, then compile.
# No benchmark or solver is run; repeating this target is safe.
confirmation-data:
	MPLCONFIGDIR=/tmp/nckh-matplotlib $(PYTHON) scripts/build_confirmation_report.py

confirmation: confirmation-data gap-data bounds-verify progress-data clique-data
	$(MAKE) pdf

# Separate completed v2 experiment; does not invoke either solver.
progress-data:
	$(PYTHON) scripts/export_progress_paper.py

# Independent post-hoc combinatorial certificates; no SAT/ILP reruns.
clique-data:
	$(PYTHON) scripts/analyze_clique_certificates.py --publish

# Post-hoc interval analysis of existing confirmation evidence; no solver calls.
gap-data:
	$(PYTHON) scripts/analyze_confirmation_gaps.py

gap-analysis: gap-data
	$(MAKE) pdf

# Audit recorded bound differences and the archived timeout capture protocol.
bounds-data:
	$(PYTHON) scripts/compare_unresolved_bounds.py

# Frozen v1 outputs remain usable after the runner moves to v2. Reconstructing
# bounds-data still requires the matching historical source checkout.
bounds-verify:
	$(PYTHON) scripts/verify_archived_bounds.py

bounds-comparison: bounds-verify
	$(MAKE) pdf

test:
	$(PYTHON) -m unittest discover -s tests -v

tree-tables:
	$(PYTHON) scripts/export_tree_screen.py

# Current manuscript: audit the completed tree screen, retain archived L(2,1) tables.
paper-figures:
	MPLCONFIGDIR=/tmp/nckh-matplotlib $(PYTHON) scripts/build_manuscript_figures.py

manuscript: tree-tables paper-figures confirmation-data gap-data bounds-verify progress-data clique-data
	$(MAKE) pdf

tables:
	$(PYTHON) scripts/export_paper_tables.py

figures:
	MPLCONFIGDIR=/tmp/nckh-matplotlib $(PYTHON) scripts/plot_symmetry_impact.py --input results/runs/cycles_main_r1.csv --output-dir paper/generated/cycles_main_r1_plots
	MPLCONFIGDIR=/tmp/nckh-matplotlib $(PYTHON) scripts/plot_symmetry_impact.py --input results/runs/products_main_r1.csv --output-dir paper/generated/products_main_r1_plots

report: tables figures tree-tables
	$(LATEXMK) -pdf -interaction=nonstopmode -halt-on-error -outdir=build main.tex

# Compile the manuscript using the already archived generated tables.
english-tables:
	$(PYTHON) scripts/export_english_tables.py

pdf: english-tables
	$(LATEXMK) -pdf -interaction=nonstopmode -halt-on-error -outdir=build main.tex
