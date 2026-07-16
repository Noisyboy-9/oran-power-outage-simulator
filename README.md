# Simulator

A custom dependable-networking simulator built with Python 3.12.

The repository implements the core `MapCell`, `User`, and `RU` domain models,
static environment construction, distance-weighted RU-to-user connectivity,
and always-active, timestamp-staggered, and battery-threshold-staggered RU
control policies. Simulation orchestration and metric calculations remain
scaffolded for later phases.

## Domain Models

- `MapCell` is an immutable map location with non-negative integer coordinates
  and an optional RU or user occupant. It calculates Cartesian distance to
  another cell.
- `User` represents a simulation user with a positive integer ID.
- `RU` represents a radio unit with a positive integer ID, battery state,
  active or sleep status, configured consumption rates, and status-based
  battery depletion.
- Invalid domain values raise `DomainValidationError`.

## Environment

The environment is configured with immutable nested configuration objects and
is fully built by its constructor:

```python
from simulator.domain import RUStatus
from simulator.environment import Environment, EnvironmentConfig, MapConfig, RUConfig

config = EnvironmentConfig(
    map=MapConfig(width=20, height=20),
    ru=RUConfig(
        count=5,
        initial_battery=100.0,
        initial_status=RUStatus.ACTIVE,
        active_consumption=2.0,
        sleep_consumption=0.5,
        coverage_radius=8.0,
    ),
    user_count=30,
    random_seed=42,
)
environment = Environment(config)
```

Construction creates a row-major map, uniform RUs, users, collision-free
placements, and an undirected NetworkX graph. Every RU and user is a graph
node. An RU-user edge exists only when their Cartesian distance is smaller than
the configured RU coverage radius.

Connection weights lie in `(0, 1]` and are randomized while scaling downward
with distance. `get_connection_weight(user, ru)` returns `0.0` when no edge
exists. A fixed random seed reproduces both placement and connection weights.

The environment does not support mobility or structural changes after
construction. Collection getters return structural copies so callers cannot
accidentally change the environment's entity membership, placement, or graph.
RU battery and status remain mutable through the RU's public methods.

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

- `src/simulator/domain`: core simulation objects (`MapCell`, `RU`, and `User`)
- `src/simulator/controllers`: the RU-controller abstraction and policies
- `src/simulator/metrics`: the metric-collector abstraction and future collectors
- `src/simulator/environment`: configuration and complete static simulation state
- `src/simulator/simulation_controller.py`: time-step orchestration
- `tests`: tests organized to mirror the source package
