# Metric Collectors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add configurable, time-indexed collectors for Average Emergency QoS, Average RU Battery Depletion Time, and Network Lifetime.

**Architecture:** `SimulationConfig` owns a validated nested metrics configuration. A template-method `MetricCollector` enforces a complete timestamp sequence while each independent concrete collector stores only its own observations and derives one final numeric value. `Simulation` emits one initial observation at `t=0` and one post-update observation per step; `main.py` composes the configured collectors and finalizes them after the simulation.

**Tech Stack:** Python 3.12, standard-library dataclasses and enums, PyYAML, pytest, Ruff, uv.

## Global Constraints

- Keep Python `>=3.12`; add no dependencies.
- `simulation.metrics` is required and has exactly `collectors` and `minimum_emergency_service_fraction` keys.
- Allowed collector names are `average_emergency_qos`, `average_ru_battery_depletion_time`, and `network_lifetime`.
- Collector names preserve YAML order; unknown and duplicate names are configuration errors; an empty list is valid.
- The SLA fraction must be a non-boolean number in `(0, 1]`.
- Every collector has a stable `name`, receives `collect(environment, timestamp)`, and returns one `float` from `finish_calculation()`.
- Collection is side-effect free and accepts exactly consecutive non-boolean integer timestamps beginning at `0`.
- `Simulation` must collect `t=0` once before its first update and after every subsequent environment update. Keep a concise comment explaining that this preserves the problem statement's metric horizon.
- An undepleted RU contributes `float("inf")` to average battery depletion time. Network lifetime is `0` for an SLA violation at `t=0`, `t - 1` for the first later violation, and `float("inf")` when the SLA never fails.
- Keep metric selection in `main.py` composition; do not make `Simulation` interpret collector names or report results.
- Run commands from the repository root with `uv run pytest`, `uv run ruff check .`, and `uv run ruff format --check .`.

---

## File Structure

- `src/simulator/configuration/models.py`: `MetricKind`, `MetricsConfig`, and the nested `SimulationConfig.metrics` field.
- `src/simulator/configuration/loader.py`: strict YAML parsing for the metrics block.
- `src/simulator/configuration/__init__.py`: public configuration exports.
- `src/simulator/metrics/base.py`: timestamp-enforcing collector template and shared finalization guard.
- `src/simulator/metrics/service.py`: one private served-user-fraction calculation shared by QoS and lifetime collectors.
- `src/simulator/metrics/average_emergency_qos.py`: QoS history and mean calculation.
- `src/simulator/metrics/average_ru_battery_depletion_time.py`: per-RU battery histories and depletion-time mean.
- `src/simulator/metrics/network_lifetime.py`: served-fraction history and SLA lifetime calculation.
- `src/simulator/metrics/factories.py`: concrete collector construction from `MetricsConfig`.
- `src/simulator/metrics/__init__.py`: public metric types and factory exports.
- `src/simulator/simulation.py`: initial collector observation plus timestamp forwarding.
- `main.py`: configured collector construction and finalization.
- `configs/default.yaml` and `README.md`: executable configuration and metric behavior documentation.
- `tests/configuration/test_models.py`, `tests/configuration/test_loader.py`: metrics schema and loader coverage.
- `tests/metrics/conftest.py`: deterministic metric test doubles.
- `tests/metrics/test_base.py`, `tests/metrics/test_service.py`, `tests/metrics/test_average_emergency_qos.py`, `tests/metrics/test_average_ru_battery_depletion_time.py`, `tests/metrics/test_network_lifetime.py`, and `tests/metrics/test_factories.py`: focused metric behavior coverage.
- `tests/test_simulation.py` and `tests/test_main.py`: lifecycle and composition coverage.

### Task 1: Add the strict metrics configuration schema

**Files:**
- Modify: `src/simulator/configuration/models.py`
- Modify: `src/simulator/configuration/loader.py`
- Modify: `src/simulator/configuration/__init__.py`
- Modify: `configs/default.yaml`
- Test: `tests/configuration/test_models.py`
- Test: `tests/configuration/test_loader.py`

**Interfaces:**
- Produces `MetricKind(StrEnum)`, `MetricsConfig(collectors: tuple[MetricKind, ...], minimum_emergency_service_fraction: float)`, and `SimulationConfig(steps: int, metrics: MetricsConfig)`.
- Produces `ApplicationConfig.simulation.metrics` after `load_config()`.

- [ ] **Step 1: Extend the test YAML and write failing loader tests**

  Add this metrics block to `VALID_YAML` immediately below `simulation.steps`:

  ```yaml
  metrics:
    collectors:
      - average_emergency_qos
      - network_lifetime
    minimum_emergency_service_fraction: 0.8
  ```

  Add tests that assert ordered typed values:

  ```python
  from simulator.configuration import MetricKind


  def test_loads_ordered_metrics_configuration(tmp_path: Path) -> None:
      metrics = load_config(write_config(tmp_path, VALID_YAML)).simulation.metrics

      assert metrics.collectors == (
          MetricKind.AVERAGE_EMERGENCY_QOS,
          MetricKind.NETWORK_LIFETIME,
      )
      assert metrics.minimum_emergency_service_fraction == 0.8

  ```

  Add exact replacement tests for each invalid value:

  ```python
  @pytest.mark.parametrize(
      ("contents", "path"),
      [
          (
              VALID_YAML.replace("    collectors:\n      - average_emergency_qos\n      - network_lifetime", "    collectors: invalid"),
              "simulation.metrics.collectors",
          ),
          (
              VALID_YAML.replace("      - network_lifetime", "      - unknown_metric"),
              "simulation.metrics.collectors",
          ),
          (
              VALID_YAML.replace("      - network_lifetime", "      - average_emergency_qos"),
              "simulation.metrics.collectors",
          ),
          (
              VALID_YAML.replace("minimum_emergency_service_fraction: 0.8", "minimum_emergency_service_fraction: 0"),
              "simulation.metrics.minimum_emergency_service_fraction",
          ),
          (
              VALID_YAML.replace("minimum_emergency_service_fraction: 0.8", "minimum_emergency_service_fraction: 1.1"),
              "simulation.metrics.minimum_emergency_service_fraction",
          ),
          (
              VALID_YAML.replace("minimum_emergency_service_fraction: 0.8", "minimum_emergency_service_fraction: true"),
              "simulation.metrics.minimum_emergency_service_fraction",
          ),
      ],
  )
  def test_rejects_invalid_metrics_configuration(
      tmp_path: Path, contents: str, path: str
  ) -> None:
      with pytest.raises(ConfigurationError, match=path):
          load_config(write_config(tmp_path, contents))
  ```

  Add separate tests for an empty list, a numeric list entry, an unknown
  `simulation.metrics` key, and the missing required metrics block.

- [ ] **Step 2: Run the configuration tests to verify they fail**

  Run: `uv run pytest tests/configuration/test_models.py tests/configuration/test_loader.py -v`

  Expected: FAIL because `SimulationConfig` has no `metrics` field and the
  current loader requires a simulation mapping containing only `steps`.

- [ ] **Step 3: Define configuration types and parsing**

  In `models.py`, add the exact types and validation:

  ```python
  class MetricKind(StrEnum):
      AVERAGE_EMERGENCY_QOS = "average_emergency_qos"
      AVERAGE_RU_BATTERY_DEPLETION_TIME = "average_ru_battery_depletion_time"
      NETWORK_LIFETIME = "network_lifetime"


  @dataclass(frozen=True)
  class MetricsConfig:
      collectors: tuple[MetricKind, ...]
      minimum_emergency_service_fraction: float

      def __post_init__(self) -> None:
          if not isinstance(self.collectors, tuple) or any(
              not isinstance(kind, MetricKind) for kind in self.collectors
          ):
              raise ValueError("collectors must contain MetricKind values")
          if len(set(self.collectors)) != len(self.collectors):
              raise ValueError("collectors must not contain duplicates")
          fraction = self.minimum_emergency_service_fraction
          if (
              isinstance(fraction, bool)
              or not isinstance(fraction, (int, float))
              or not 0 < fraction <= 1
          ):
              raise ValueError(
                  "minimum_emergency_service_fraction must be a number between 0 and 1"
              )
  ```

  Add `metrics: MetricsConfig` to `SimulationConfig`. In `_parse_simulation`,
  require exactly `{"steps", "metrics"}`, require a mapping for `metrics`, and
  parse its exact keys. Convert each string to `MetricKind`, rejecting unknown,
  non-string, and duplicate values with the collector path. Use
  `_require_number()` followed by `MetricsConfig` for the SLA value. Export
  `MetricKind` and `MetricsConfig` from `simulator.configuration`.

- [ ] **Step 4: Update direct model tests and the default configuration**

  Update the existing direct `SimulationConfig(steps=...)` tests to supply a
  valid `MetricsConfig`. Add model tests that construct an empty collector tuple
  and reject a list, duplicate kinds, booleans, `0`, and values above `1`.
  Update the default YAML to select all three metric kinds and set the SLA value
  to `0.8`.

- [ ] **Step 5: Run the focused tests to verify the schema passes**

  Run: `uv run pytest tests/configuration/test_models.py tests/configuration/test_loader.py -v`

  Expected: PASS. Update each direct `ApplicationConfig` fixture in
  `tests/test_simulation.py` in Task 4 before the full-suite run.

- [ ] **Step 6: Commit the configuration schema**

  ```bash
  git add src/simulator/configuration/models.py src/simulator/configuration/loader.py src/simulator/configuration/__init__.py configs/default.yaml tests/configuration/test_models.py tests/configuration/test_loader.py
  git commit -m "feat: configure metric collectors"
  ```

### Task 2: Establish the collector lifecycle and shared service observation

**Files:**
- Modify: `src/simulator/metrics/base.py`
- Create: `src/simulator/metrics/service.py`
- Modify: `src/simulator/metrics/__init__.py`
- Create: `tests/metrics/conftest.py`
- Modify: `tests/metrics/test_base.py`
- Create: `tests/metrics/test_service.py`

**Interfaces:**
- Produces the abstract `MetricCollector` template with `name`,
  `collect(environment: Environment, timestamp: int) -> None`, and
  `finish_calculation() -> float`.
- Produces private `_served_user_fraction(environment: Environment) -> float`.

- [ ] **Step 1: Write failing timestamp and service tests**

  Create a minimal recording subclass in `test_base.py`:

  ```python
  class RecordingCollector(MetricCollector):
      name = "recording"

      def __init__(self) -> None:
          super().__init__()
          self.timestamps: list[int] = []

      def _collect(self, environment: Environment, timestamp: int) -> None:
          self.timestamps.append(timestamp)

      def finish_calculation(self) -> float:
          self._require_observation()
          return float(len(self.timestamps))
  ```

  Test that `MetricCollector()` remains abstract, `finish_calculation()` fails
  before a collection, valid calls at `0` then `1` are retained, and calls at
  `-1`, `True`, `1` as the first timestamp, duplicate `0`, and skipped `2`
  after `0` raise `ValueError`.

  In `conftest.py`, provide a small `FakeEnvironment` with `get_users()`,
  `get_rus()`, and `get_connection_weight()`, plus real `User` and `RU`
  instances. In `test_service.py`, assert that no active connection returns
  `0.0`, one active connection serves a user, a sleeping connected RU does not,
  and two active RUs connected to one user count that user once.

- [ ] **Step 2: Run the metric tests to verify they fail**

  Run: `uv run pytest tests/metrics/test_base.py tests/metrics/test_service.py -v`

  Expected: FAIL because the existing collector accepts only an environment,
  exposes no lifecycle helper, and the shared service helper does not exist.

- [ ] **Step 3: Implement the template-method collector and helper**

  Replace the base class with a concrete `collect()` template around two
  abstract hooks:

  ```python
  class MetricCollector(ABC):
      def __init__(self) -> None:
          self._last_collected_timestamp: int | None = None

      @property
      @abstractmethod
      def name(self) -> str:
          """Return the stable configuration name for this collector."""

      def collect(self, environment: Environment, timestamp: int) -> None:
          expected_timestamp = (
              0
              if self._last_collected_timestamp is None
              else self._last_collected_timestamp + 1
          )
          if (
              isinstance(timestamp, bool)
              or not isinstance(timestamp, int)
              or timestamp != expected_timestamp
          ):
              raise ValueError("timestamp must be the next non-negative integer")
          self._collect(environment, timestamp)
          self._last_collected_timestamp = timestamp

      @abstractmethod
      def _collect(self, environment: Environment, timestamp: int) -> None:
          """Record this collector's observation for one timestamp."""

      def _require_observation(self) -> None:
          if self._last_collected_timestamp is None:
              raise ValueError("cannot finish a metric before collecting an observation")

      @abstractmethod
      def finish_calculation(self) -> float:
          """Return this metric after its final observation."""
  ```

  In `service.py`, loop over users and use `any()` across RUs, requiring both
  `ru.get_status() is RUStatus.ACTIVE` and
  `environment.get_connection_weight(user, ru) > 0.0`. Return the served count
  divided by the user count. The helper only reads public environment and RU
  APIs.

- [ ] **Step 4: Run the focused tests to verify they pass**

  Run: `uv run pytest tests/metrics/test_base.py tests/metrics/test_service.py -v`

  Expected: PASS. The metric test doubles prove timestamp validation and no
  state mutation; the service tests prove active, connected coverage semantics.

- [ ] **Step 5: Commit the metric foundation**

  ```bash
  git add src/simulator/metrics/base.py src/simulator/metrics/service.py src/simulator/metrics/__init__.py tests/metrics/conftest.py tests/metrics/test_base.py tests/metrics/test_service.py
  git commit -m "feat: add metric observation foundation"
  ```

### Task 3: Implement and test the three independent collectors

**Files:**
- Create: `src/simulator/metrics/average_emergency_qos.py`
- Create: `src/simulator/metrics/average_ru_battery_depletion_time.py`
- Create: `src/simulator/metrics/network_lifetime.py`
- Modify: `src/simulator/metrics/__init__.py`
- Create: `tests/metrics/test_average_emergency_qos.py`
- Create: `tests/metrics/test_average_ru_battery_depletion_time.py`
- Create: `tests/metrics/test_network_lifetime.py`

**Interfaces:**
- Produces `AverageEmergencyQoSCollector`, `AverageRUBatteryDepletionTimeCollector`, and `NetworkLifetimeCollector(minimum_emergency_service_fraction: float)`.
- Each class inherits `MetricCollector`, provides the matching string name, and returns a `float` from `finish_calculation()`.

- [ ] **Step 1: Write failing QoS tests**

  Using `FakeEnvironment`, verify the named collector records a zero fraction,
  a complete fraction, and a partial fraction across timestamps `0`, `1`, and
  `2` and returns their arithmetic mean. Include the following exact assertion
  for duplicate active coverage:

  ```python
  collector.collect(environment_with_one_user_and_two_active_connections, 0)

  assert collector.finish_calculation() == 1.0
  ```

  Capture RU battery, status, and the fake connection map before and after
  `collect()` and assert they are unchanged.

- [ ] **Step 2: Write failing battery-depletion tests**

  Give a fake environment two RUs whose batteries are adjusted between calls.
  Assert first zero values determine the average:

  ```python
  collector.collect(environment, 0)  # {1: 2.0, 2: 3.0}
  set_batteries(environment, {1: 0.0, 2: 1.0})
  collector.collect(environment, 1)
  set_batteries(environment, {1: 0.0, 2: 0.0})
  collector.collect(environment, 2)

  assert collector.finish_calculation() == 1.5
  ```

  Add tests for an exact-zero observation at `t=0`, later values not replacing
  a first depletion, and `math.isinf()` when one or both RUs remain positive.

- [ ] **Step 3: Write failing network-lifetime tests**

  With a threshold of `0.5`, verify equality passes, the first violation at
  `t=2` returns `1.0`, recovery at `t=3` does not alter that value, a violation
  at `t=0` returns `0.0`, and uninterrupted passing observations return an
  infinite result:

  ```python
  collector.collect(environment_serving_all_users, 0)
  collector.collect(environment_serving_exactly_half_of_users, 1)
  collector.collect(environment_serving_no_users, 2)

  assert collector.finish_calculation() == 1.0
  ```

  Add direct-construction validation for invalid thresholds `0`, `1.1`,
  `True`, and a string.

- [ ] **Step 4: Run the collector tests to verify they fail**

  Run: `uv run pytest tests/metrics/test_average_emergency_qos.py tests/metrics/test_average_ru_battery_depletion_time.py tests/metrics/test_network_lifetime.py -v`

  Expected: FAIL during collection because the concrete collector modules do
  not exist.

- [ ] **Step 5: Implement the concrete collectors**

  Use the base lifecycle rather than reimplementing timestamp checks. The QoS
  collector stores `dict[int, float]` fractions and calculates:

  ```python
  def finish_calculation(self) -> float:
      self._require_observation()
      return sum(self._served_fractions.values()) / len(self._served_fractions)
  ```

  The battery collector stores `dict[int, dict[int, float]]`. In finalization,
  use the RU IDs from the `t=0` snapshot, scan timestamp order for each ID's
  first value `<= 0`, substitute `float("inf")` when no value qualifies, and
  return their arithmetic mean.

  The network-lifetime collector validates and stores its SLA fraction in the
  constructor, stores `dict[int, float]` fractions, then returns `0.0` for a
  failing `t=0`, `float(timestamp - 1)` for the first later failure, or
  `float("inf")` when none fail. Compare with `<`, not `<=`, so equality meets
  the SLA.

  Export all three classes from `simulator.metrics`.

- [ ] **Step 6: Run the focused collector tests to verify they pass**

  Run: `uv run pytest tests/metrics/test_average_emergency_qos.py tests/metrics/test_average_ru_battery_depletion_time.py tests/metrics/test_network_lifetime.py -v`

  Expected: PASS, including zero, boundary, recovery, infinity, and
  side-effect assertions.

- [ ] **Step 7: Commit the collector implementations**

  ```bash
  git add src/simulator/metrics/average_emergency_qos.py src/simulator/metrics/average_ru_battery_depletion_time.py src/simulator/metrics/network_lifetime.py src/simulator/metrics/__init__.py tests/metrics/test_average_emergency_qos.py tests/metrics/test_average_ru_battery_depletion_time.py tests/metrics/test_network_lifetime.py
  git commit -m "feat: add network metric collectors"
  ```

### Task 4: Compose collectors and preserve the initial observation

**Files:**
- Create: `src/simulator/metrics/factories.py`
- Modify: `src/simulator/metrics/__init__.py`
- Modify: `src/simulator/simulation.py`
- Modify: `main.py`
- Create: `tests/metrics/test_factories.py`
- Modify: `tests/test_simulation.py`
- Modify: `tests/test_main.py`

**Interfaces:**
- Produces `build_metric_collectors(config: MetricsConfig) -> list[MetricCollector]`.
- `Simulation` invokes `collector.collect(self.environment, timestamp)` at `t=0` once and after each environment update.
- `main.main()` builds configured collectors, passes them to `Simulation`, calls `simulate()`, then calls `finish_calculation()` once on every collector.

- [ ] **Step 1: Write failing factory tests**

  Assert that the factory creates classes in configuration order and provides
  the SLA fraction to the lifetime collector:

  ```python
  collectors = build_metric_collectors(
      MetricsConfig(
          collectors=(MetricKind.NETWORK_LIFETIME, MetricKind.AVERAGE_EMERGENCY_QOS),
          minimum_emergency_service_fraction=0.75,
      )
  )

  assert [collector.name for collector in collectors] == [
      "network_lifetime",
      "average_emergency_qos",
  ]
  assert isinstance(collectors[0], NetworkLifetimeCollector)
  assert collectors[0].minimum_emergency_service_fraction == 0.75
  ```

  Also assert an empty configuration returns `[]`.

- [ ] **Step 2: Write failing simulation lifecycle tests**

  Replace the existing recording collector with one that stores received
  timestamps and environment states. Assert a two-step run produces `[0, 1, 2]`
  and that the first record observes the initial battery/status before
  `Environment.update(1)`. Call `simulate()` again and assert the next records
  are `[3, 4]`, not a second `0`.

  Update every direct `ApplicationConfig(...)` fixture to include:

  ```python
  metrics=MetricsConfig(
      collectors=(), minimum_emergency_service_fraction=0.8
  )
  ```

- [ ] **Step 3: Write failing main-composition tests**

  In `test_main.py`, give the fake loaded config a `metrics` attribute, mock
  `build_metric_collectors` to return two fake
  collectors and make `FakeSimulation.simulate()` append an event. Each fake
  collector's `finish_calculation()` appends its name. Assert the exact order:

  ```python
  assert events == [
      ("load", Path("example.yaml")),
      ("configure_logging", logging_config),
      ("build_collectors", metrics_config),
      ("construct", config, fake_collectors),
      "simulate",
      "finish:first",
      "finish:second",
  ]
  ```

- [ ] **Step 4: Run factory, simulation, and main tests to verify they fail**

  Run: `uv run pytest tests/metrics/test_factories.py tests/test_simulation.py tests/test_main.py -v`

  Expected: FAIL because no factory exists, collectors receive no timestamp,
  `t=0` is not collected, and `main.py` still passes an empty tuple.

- [ ] **Step 5: Implement factory, lifecycle, and finalization**

  In `factories.py`, map every `MetricKind` explicitly to its concrete class;
  pass the configured SLA fraction only to `NetworkLifetimeCollector`. Return a
  new list in the input order.

  In `Simulation.__init__`, add `_initial_metrics_collected = False`. At the
  start of `simulate()`, call a private `_collect_initial_metrics()` that returns
  immediately when the flag is true; otherwise it executes:

  ```python
  # Metrics include the initial state because their definitions start at t=0.
  for collector in self._metric_collectors:
      collector.collect(self._environment, self._timestamp)
  self._initial_metrics_collected = True
  ```

  Change the post-update loop in `_step()` to call
  `collector.collect(self._environment, self._timestamp)`.

  In `main.py`, create `metric_collectors` with
  `build_metric_collectors(config.simulation.metrics)`, pass that list to
  `Simulation`, call `simulate()`, then iterate that same list and call
  `finish_calculation()` exactly once per collector. Do not add output or
  logging behavior in this task.

- [ ] **Step 6: Run the focused integration tests to verify they pass**

  Run: `uv run pytest tests/metrics/test_factories.py tests/test_simulation.py tests/test_main.py -v`

  Expected: PASS. The event test proves construction and finalization order;
  the simulation test proves one initial observation and post-update timing.

- [ ] **Step 7: Commit the composed lifecycle**

  ```bash
  git add src/simulator/metrics/factories.py src/simulator/metrics/__init__.py src/simulator/simulation.py main.py tests/metrics/test_factories.py tests/test_simulation.py tests/test_main.py
  git commit -m "feat: collect configured simulation metrics"
  ```

### Task 5: Document the final configuration and verify the complete change

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-07-25-metric-collectors-design.md` only if implementation required a documented correction

**Interfaces:**
- Documents the final `simulation.metrics` YAML contract and post-run collector finalization boundary.

- [ ] **Step 1: Update README usage and configuration documentation**

  Add the `simulation.metrics` example with all three collector names and a
  `minimum_emergency_service_fraction` of `0.8`. State that observations include
  the initial `t=0` state and each post-update state, then summarize the three
  result rules: QoS mean, infinity for unobserved RU depletion, and infinity
  when the SLA is never violated. Explain that `main.py` constructs configured
  collectors and finalizes them after simulation without claiming result output
  formatting exists.

- [ ] **Step 2: Run all tests**

  Run: `uv run pytest`

  Expected: PASS with all existing tests plus new configuration, collector,
  factory, lifecycle, and main-composition tests passing.

- [ ] **Step 3: Run lint and format verification**

  Run: `uv run ruff check .`

  Expected: exit code `0`.

  Run: `uv run ruff format --check .`

  Expected: exit code `0`.

- [ ] **Step 4: Review the complete diff**

  Run: `git diff --check HEAD`

  Expected: no whitespace errors.

  Run: `git status --short`

  Expected: only the metric implementation, tests, configuration, documentation,
  and approved design/plan changes are present.

- [ ] **Step 5: Commit the documentation**

  ```bash
  git add README.md docs/superpowers/specs/2026-07-25-metric-collectors-design.md
  git commit -m "docs: describe configured metric collection"
  ```
