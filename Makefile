.PHONY: install run visual debug test clean lint lint-strict

VENV := venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
SYSTEM_PYTHON := $(shell command -v python3.12 || command -v python3.11 \
	|| command -v python3.10 || command -v python3)

MAP ?= maps/easy/01_linear_path.txt
ARGS ?=

install:
	rm -rf $(VENV)
	$(SYSTEM_PYTHON) -m venv $(VENV) 2>/dev/null \
		|| (rm -rf $(VENV) && $(SYSTEM_PYTHON) -m virtualenv $(VENV))
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

run:
	$(PYTHON) main.py $(MAP) $(ARGS)

visual:
	$(PYTHON) main.py $(MAP) --visual $(ARGS)

debug:
	$(PYTHON) -m pdb main.py $(MAP) $(ARGS)

test:
	$(PYTHON) -m pytest -q

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	rm -rf .mypy_cache .pytest_cache

lint:
	$(VENV)/bin/flake8 .
	$(VENV)/bin/mypy . --warn-return-any --warn-unused-ignores \
		--ignore-missing-imports --disallow-untyped-defs \
		--check-untyped-defs

lint-strict:
	$(VENV)/bin/flake8 .
	$(VENV)/bin/mypy . --strict
