# Simulator

A custom dependable-networking simulator built with Python 3.12.

The repository implements the core `MapCell`, `User`, and `RU` domain models,
static environment construction, distance-weighted RU-to-user connectivity,
always-active, timestamp-staggered, and battery-threshold-staggered RU control
policies, and configured metric collection.

## Domain Models

- `MapCell` is an immutable map location with non-negative integer coordinates
  and an optional RU or user occupant. It calculates Cartesian distance to
  another cell.
- `User` represents a simulation user with a positive integer ID.
- `RU` represents a radio unit with a positive integer ID, battery state,
  active or sleep status, zero-user, one-user, and multi-user-per-user active
  consumption rates, a sleep consumption rate, and load-aware battery depletion.
- Invalid domain values raise `DomainValidationError`.

## Environment

The environment is configured with immutable nested configuration objects and
is fully built by its constructor:

```python
from simulator.controllers import AlwaysActiveController
from simulator.domain import RUStatus
from simulator.environment import Environment, EnvironmentConfig, MapConfig, RUConfig

config = EnvironmentConfig(
    map=MapConfig(width=20, height=20),
    ru=RUConfig(
        count=5,
        user_capacity=100,
        initial_battery=100.0,
        initial_status=RUStatus.ACTIVE,
        zero_user_consumption=1.0,
        one_user_consumption=2.0,
        multi_user_consumption_per_user=1.5,
        sleep_consumption=0.5,
        coverage_radius=8.0,
    ),
    user_count=30,
    random_seed=42,
)
controller = AlwaysActiveController()
environment = Environment(
    config,
    controller,
    minimum_service_link_weight=0.6,
)
```

Construction creates a row-major map, uniform RUs, users, collision-free
placements, and an undirected NetworkX graph. Every RU and user is a graph
node. An RU-user edge exists only when their Cartesian distance is smaller than
the configured RU coverage radius. This connectivity graph contains every
in-range weighted possibility; the environment-owned association map contains
one accepted RU or `None` per user.

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
least the configured zero-user active consumption available for one timestamp.

- `AlwaysActiveController` activates every eligible RU.
- `StaggeredActiveController` alternates even- and odd-ID groups every ten
  global timestamps.
- `ThresholdStaggeredActiveController` keeps all eligible RUs active until every
  RU reaches a configured percentage of its initial capacity, then permanently
  follows the global staggered schedule.

Battery depletion remains the RU's responsibility through `update_battery()`;
controllers only select statuses.

## Simulation

`Simulation` is the entry point for one already-loaded `ApplicationConfig`.
It creates the environment and configured RU controller, starts at timestamp
`0`, and accepts optional metric collector instances. Calling `simulate()` runs
the positive `simulation.steps` count from configuration. Each private step
increments the timestamp, then charges prior associations, applies the RU
controller, rebuilds possible links, rebuilds associations, and collects
metrics. Associations admit one active, charged RU per user, subject to each
RU's `user_capacity` and the configured `minimum_service_link_weight`.

```python
from pathlib import Path

from simulator.configuration import load_config
from simulator.simulation import Simulation

config = load_config(Path("configs/default.yaml"))
simulation = Simulation(config)
simulation.simulate()
```

`main.py` is the application entry point: it loads configuration, configures
logging, constructs configured metric collectors, starts `Simulation`, and
finalizes each collector after the simulation completes. It does not define
metric result output formatting.

## Logging

With `configs/default.yaml`, the simulator uses `structlog` to emit
INFO-and-higher events as one JSON object per line on standard output. That
default configuration includes a UTC `logged_at` timestamp, leaving domain
fields such as the simulation `timestamp` intact. `simulator.logging` is the
package's public configuration entry point. Load configuration once at setup
and pass it explicitly to each component; it is not held in a global singleton:

```python
from pathlib import Path

from simulator.configuration import build_controller, load_config
from simulator.environment import Environment
from simulator.logging import configure_logging

config = load_config(Path("configs/default.yaml"))
configure_logging(config.logging)
controller = build_controller(config.controller)
environment = Environment(
    config.environment,
    controller,
    config.simulation.metrics.minimum_service_link_weight,
)
```

Modules obtain their own named logger and attach domain data as fields:

```python
import structlog

logger = structlog.get_logger(__name__)
logger.info("simulation_started", timestamp=0)
```

## Running a Simulation

Run the application with the required YAML configuration path and required
metric output directory:

```bash
uv run python main.py --configs configs/default.yaml --metrics-output-path outputs/run-001
```

The required configuration's `simulation.steps` value determines how many ordered simulation steps run. `main.py` loads configuration, configures logging, constructs configured metric collectors, and starts `Simulation`. `Simulation` owns the ordered step loop.

### Metrics

Configure the collectors to run in `simulation.metrics`:

```yaml
simulation:
  steps: 10000
  metrics:
    collectors:
      - average_emergency_qos
      - average_ru_battery_depletion_time
      - network_lifetime
    minimum_emergency_service_fraction: 0.8
    minimum_service_link_weight: 0.6
```

Collectors observe the initial `t=0` state and each post-update state. Average
Emergency QoS is the mean of its observed served-user fractions. Average RU
Battery Depletion Time is infinity when any RU has no observed depletion. Network
Lifetime is infinity when the service-level agreement is never violated over the
observed horizon. RUs whose links are below `minimum_service_link_weight` are
never contacted for those users. The environment applies that threshold when it
creates associations, together with RU availability and capacity rules. An
accepted association alone then represents service; QoS and Network Lifetime
observe that association without rechecking RU status, battery, graph edges, or
connection weight.

### Metric output files

Each selected collector writes one stable-name JSON file in
`--metrics-output-path`: `average_emergency_qos.json`,
`average_ru_battery_depletion_time.json`, or `network_lifetime.json`. Only
collectors selected in `simulation.metrics.collectors` write files. The first
JSON member, `input_configuration`, contains the complete loaded configuration.
The remaining result body has this compact form:

```json
{
  "collector": "average_emergency_qos",
  "observations": [{"timestamp": 0, "served_user_fraction": 1.0}],
  "final_result": 1.0
}
```

The Average Emergency QoS and Network Lifetime collectors record observations
with `timestamp` and `served_user_fraction`. Battery-depletion observations
contain `timestamp` and a `ru_batteries` map whose RU-ID keys are strings.
`final_result` is a JSON number when finite and the JSON literal `null` when
the calculated value is infinite; the string `"null"` is never written.
Repeated runs using the same output directory overwrite files with the same
name.

## Setup

Install [uv](https://docs.astral.sh/uv/), then synchronize the development environment:

```bash
uv sync --dev
```

The Makefile provides common project commands:

```bash
make test
make run
make run-all
make lint
make format
make check
```

`make run` uses `configs/default.yaml` and writes metric files to
`outputs/default`. Override either value as needed, for example:

```bash
make run CONFIG=configs/experiment.yaml METRICS_OUTPUT_PATH=outputs/experiment
```

Use `make run-all` to run all three policy scenarios, writing metrics to a
separate directory for each policy.

Run `make help` to see all available targets, including `make sync` for
environment synchronization.

## Structure

- `src/simulator/domain`: core simulation objects (`MapCell`, `RU`, and `User`)
- `src/simulator/controllers`: the RU-controller abstraction and policies
- `src/simulator/metrics`: the metric-collector abstraction and collectors
- `src/simulator/environment`: configuration and complete static simulation state
- `src/simulator/simulation.py`: time-step orchestration
- `tests`: tests organized to mirror the source package
