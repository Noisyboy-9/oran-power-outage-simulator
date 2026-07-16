# Simulator

A custom dependable-networking simulator built with Python 3.12.

The repository currently implements the core `Point`, `User`, and `RU` domain
models plus always-active, timestamp-staggered, and battery-threshold-staggered
RU control policies. Simulation orchestration and metric calculations remain
scaffolded for later phases.

## Domain Models

- `Point` represents non-negative Cartesian coordinates and calculates distance
  to another point.
- `User` represents a simulation user with a positive integer ID.
- `RU` represents a radio unit with a positive integer ID, battery state,
  active or sleep status, configured consumption rates, and status-based
  battery depletion.
- Invalid constructor values raise `DomainValidationError`.

## RU Controllers

Each controller receives a list of RUs and the current timestamp, then updates
RU statuses in place for that timestamp. An RU is activated only when it has at
least enough battery for one active timestamp.

- `AlwaysActiveController` activates every eligible RU.
- `StaggeredActiveController` alternates even- and odd-ID groups every ten
  global timestamps.
- `ThresholdStaggeredActiveController` keeps all eligible RUs active until every
  RU reaches a configured percentage of its initial capacity, then permanently
  follows the global staggered schedule.

Battery depletion remains the RU's responsibility through `update_battery()`;
controllers only select statuses.

## Logging

The simulator uses `structlog` and emits INFO-and-higher events as one JSON
object per line on standard output. Each event includes a UTC `logged_at`
timestamp, leaving domain fields such as the simulation `timestamp` intact.
Configure logging once in the future application entry point before running the
simulation:

```python
from simulator.logging import configure_logging

configure_logging()
```

Modules obtain their own named logger and attach domain data as fields:

```python
import structlog

logger = structlog.get_logger(__name__)
logger.info("simulation_started", timestamp=0)
```

## Setup

Install [uv](https://docs.astral.sh/uv/), then synchronize the development environment:

```bash
uv sync --dev
```

Run project tools through uv:

```bash
uv run pytest
uv run ruff check .
uv run ruff format .
```

## Structure

- `src/simulator/domain`: core simulation objects (`Point`, `RU`, and `User`)
- `src/simulator/controllers`: the RU-controller abstraction and policies
- `src/simulator/metrics`: the metric-collector abstraction and future collectors
- `src/simulator/environment.py`: the complete simulation environment
- `src/simulator/simulation_controller.py`: time-step orchestration
- `tests`: tests organized to mirror the source package
