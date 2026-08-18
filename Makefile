.DEFAULT_GOAL := help

CONFIG ?= configs/default.yaml

.PHONY: help sync test run lint format check

help:
	@printf '%s\n' \
		'Simulator development targets:' \
		'  make sync                 Synchronize the development environment.' \
		'  make test                 Run the test suite.' \
		'  make run [CONFIG=path]    Run the simulator with a configuration file.' \
		'  make lint                 Run Ruff lint checks.' \
		'  make format               Apply Ruff formatting.' \
		'  make check                Run tests, lint, and formatting checks.'

sync:
	uv sync --dev

test:
	uv run pytest

run:
	uv run python main.py --configs $(CONFIG)

lint:
	uv run ruff check .

format:
	uv run ruff format .

check: test lint
	uv run ruff format --check .
