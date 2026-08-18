.DEFAULT_GOAL := help

CONFIG ?= configs/default.yaml
METRICS_OUTPUT_PATH ?= outputs/default
ITERATIONS := $(shell seq -w 1 10)
POLICIES := always_active staggered_active threshold_staggered_active

.PHONY: help sync test run run-all lint format check

help:
	@printf '%s\n' \
		'Simulator development targets:' \
		'  make sync                 Synchronize the development environment.' \
		'  make test                 Run the test suite.' \
		'  make run [CONFIG=path METRICS_OUTPUT_PATH=path] Run the simulator.' \
		'  make run-all              Run all 10 seeds × 3 policy scenarios and write outputs beneath outputs/.' \
		'  make lint                 Run Ruff lint checks.' \
		'  make format               Apply Ruff formatting.' \
		'  make check                Run tests, lint, and formatting checks.'

sync:
	uv sync --dev

test:
	uv run pytest

run:
	uv run python main.py --configs $(CONFIG) --metrics-output-path $(METRICS_OUTPUT_PATH)

run-all:
	@set -e; for iteration in $(ITERATIONS); do \
		for policy in $(POLICIES); do \
			$(MAKE) run CONFIG=configs/iteration-$$iteration/$$policy.yaml \
				METRICS_OUTPUT_PATH=outputs/iteration-$$iteration/$$policy; \
		done; \
	done

lint:
	uv run ruff check .

format:
	uv run ruff format .

check: test lint
	uv run ruff format --check .
