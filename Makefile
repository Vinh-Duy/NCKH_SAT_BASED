PYTHON ?= .venv-1/bin/python
LATEXMK ?= /Library/TeX/texbin/latexmk

.PHONY: test report tables figures

test:
	$(PYTHON) -m unittest discover -s tests -v

tables:
	$(PYTHON) scripts/export_paper_tables.py

figures:
	MPLCONFIGDIR=/tmp/nckh-matplotlib $(PYTHON) scripts/plot_symmetry_impact.py --input results/runs/cycles_main_r1.csv --output-dir paper/generated/cycles_main_r1_plots
	MPLCONFIGDIR=/tmp/nckh-matplotlib $(PYTHON) scripts/plot_symmetry_impact.py --input results/runs/products_main_r1.csv --output-dir paper/generated/products_main_r1_plots

report: tables figures
	$(LATEXMK) -pdf -interaction=nonstopmode -halt-on-error -outdir=build main.tex
