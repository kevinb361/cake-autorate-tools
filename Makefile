.PHONY: test lint ci

PYTHON ?= python3
SHELL_SCRIPTS := scripts/rrul-slot.sh scripts/capacity-sweep.sh scripts/silicom-bypass \
	scripts/wanctl-bpctl-watchdog-petter scripts/wanctl-bpctl-watchdog-bypass deploy/systemd/wanctl-bpctl-init
PY_SCRIPTS := deploy/scripts/cake-autorate-state-bridge deploy/scripts/cake-metrics-exporter \
	scripts/rrul_shadow_analyzer.py

# With pytest-xdist, --dist=loadfile keeps each module's tests on one worker: the capacity-sweep tests must not run
# concurrently with each other.
XDIST := $(shell $(PYTHON) -c 'import xdist' 2>/dev/null && echo "-n auto --dist=loadfile")

# Synthetic tests only: every network, load and service tool is a fake.
test:
	$(PYTHON) -m pytest tests/ -q $(XDIST)

lint:
	ruff check tests/ $(PY_SCRIPTS)
	shellcheck --severity=error $(SHELL_SCRIPTS)

ci: lint test
