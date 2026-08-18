.DEFAULT_GOAL := help

CONFIG ?= configs/default.yaml
METRICS_OUTPUT_PATH ?= outputs/default

.PHONY: help sync test run run-all lint format check

help:
	@printf '%s\n' \
		'Simulator development targets:' \
		'  make sync                 Synchronize the development environment.' \
		'  make test                 Run the test suite.' \
		'  make run [CONFIG=path METRICS_OUTPUT_PATH=path] Run the simulator.' \
		'  make run-all              Run all policy scenarios.' \
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
	uv run python main.py --configs configs/always_active.yaml --metrics-output-path outputs/always_active
	uv run python main.py --configs configs/staggered_active.yaml --metrics-output-path outputs/staggered_active
	uv run python main.py --configs configs/threshold_staggered_active.yaml --metrics-output-path outputs/threshold_staggered_active

lint:
	uv run ruff check .

format:
	uv run ruff format .

check: test lint
	uv run ruff format --check .
