# make test  -> every check: print, assembly, BOM, calc gates, sim results, firmware host tests, electronics
# make all   -> rebuild everything from params (CAD ~2 min, FEA ~15 min, feed 2 min, Monte Carlo ~20 min)
PY ?= .venv/bin/python

.PHONY: test test-fast all cad calc sim fea feed mc validate docs bom firmware zip clean

test:
	$(PY) -m pytest tests electronics/test_electronics.py -q

test-fast:  ## skips the slow assembly sweeps
	$(PY) -m pytest tests electronics/test_electronics.py -q --deselect tests/test_assembly.py

all: cad calc sim docs test

cad:
	$(PY) -m cad.build

calc:
	$(PY) -m calc.run_all

sim: fea feed mc validate

fea:
	$(PY) -m sim.fea

feed:
	$(PY) -m sim.feed_sim -n 300

mc:
	$(PY) -m sim.monte_carlo

validate:
	$(PY) -m sim.validate

bom:
	$(PY) tools/bom.py

docs: bom
	$(PY) electronics/make_wiring.py
	$(PY) tools/gen_docs.py

firmware:
	bash firmware/tools/host_tests.sh

zip:
	cd .. && rm -f beer-launcher.zip && zip -qr beer-launcher.zip beer-launcher -x "beer-launcher/.venv/*" "*/__pycache__/*" "beer-launcher/.git/*" "*.pytest_cache*"
