# Service Link Threshold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Require a configured minimum service-link weight, active status, positive battery, and a real graph edge before a user counts as served for QoS and Network Lifetime.

**Architecture:** Add the threshold to `MetricsConfig`, pass it through the existing metric factory to the two service-based collectors, and make the shared service helper enforce all four served-user conditions. The environment graph and battery/controller behavior stay unchanged; battery-depletion metrics remain independent.

**Tech Stack:** Python 3.12, dataclasses, PyYAML, NetworkX, pytest, Ruff, uv.

## Global Constraints

- Add required `simulation.metrics.minimum_service_link_weight`.
- The threshold is a non-boolean number in the inclusive range `[0, 1]`; `0.0` is valid.
- A served user requires an existing graph edge, `RUStatus.ACTIVE`, `ru.get_battery() > 0`, and edge weight `>= minimum_service_link_weight`.
- An absent edge must not serve a user when the threshold is `0.0`.
- Only Average Emergency QoS and Network Lifetime receive the threshold; battery depletion remains unchanged.
- Do not alter connectivity graph membership or weights, controller behavior, battery consumption, metric timestamps, output formatting, or dependencies.
- Run `uv run pytest`, `uv run ruff check .`, and `uv run ruff format --check .` from the repository root before completion.

---

## File Structure

- `src/simulator/configuration/models.py`: adds `MetricsConfig.minimum_service_link_weight` and validation.
- `src/simulator/configuration/loader.py`: requires and parses the new YAML key.
- `configs/default.yaml`: supplies the default threshold.
- `tests/configuration/test_models.py` and `tests/configuration/test_loader.py`: validate direct construction and strict YAML loading.
- `src/simulator/metrics/service.py`: checks graph-edge existence, status, battery, and threshold.
- `src/simulator/metrics/average_emergency_qos.py` and `src/simulator/metrics/network_lifetime.py`: accept and preserve the threshold.
- `tests/metrics/conftest.py`, `tests/metrics/test_service.py`, `tests/metrics/test_average_emergency_qos.py`, and `tests/metrics/test_network_lifetime.py`: deterministic threshold boundary coverage.
- `src/simulator/metrics/factories.py` and `tests/metrics/test_factories.py`: pass the configured threshold to exactly the service-based collectors.
- `README.md`: documents the configuration and serving rule.

### Task 1: Add the strict service-link threshold configuration

**Files:**
- Modify: `src/simulator/configuration/models.py`
- Modify: `src/simulator/configuration/loader.py`
- Modify: `src/simulator/configuration/__init__.py` only if an export changes
- Modify: `configs/default.yaml`
- Modify: `tests/configuration/test_models.py`
- Modify: `tests/configuration/test_loader.py`
- Modify: `tests/test_simulation.py`

**Interfaces:**
- Produces `MetricsConfig(collectors, minimum_emergency_service_fraction, minimum_service_link_weight)`.
- Produces `config.simulation.metrics.minimum_service_link_weight: float` after YAML loading.

- [ ] **Step 1: Write failing model and loader tests**

  Extend the valid metrics YAML with:

  ```yaml
  minimum_service_link_weight: 0.3
  ```

  Add direct model tests for `0.0`, `0.3`, and `1.0`, plus invalid values:

  ```python
  @pytest.mark.parametrize("threshold", [0.0, 0.3, 1.0])
  def test_metrics_config_accepts_service_link_weight(
      threshold: float,
  ) -> None:
      config = MetricsConfig(
          collectors=(),
          minimum_emergency_service_fraction=0.8,
          minimum_service_link_weight=threshold,
      )

      assert config.minimum_service_link_weight == threshold


  @pytest.mark.parametrize("threshold", [-0.1, 1.1, True, "0.3"])
  def test_metrics_config_rejects_invalid_service_link_weight(
      threshold: object,
  ) -> None:
      with pytest.raises(ValueError, match="minimum_service_link_weight"):
          MetricsConfig((), 0.8, threshold)  # type: ignore[arg-type]
  ```

  Add loader tests that reject a missing key, `false`, `-0.1`, `1.1`, and an
  unknown metrics key while asserting the precise dotted configuration path.
  Update every direct `MetricsConfig` and `ApplicationConfig` fixture to include
  a valid threshold of `0.0` or `0.3`.

- [ ] **Step 2: Run configuration tests to verify they fail**

  Run: `uv run pytest tests/configuration/test_models.py tests/configuration/test_loader.py tests/test_simulation.py -v`

  Expected: FAIL because `MetricsConfig` lacks the third required field and the
  loader treats `minimum_service_link_weight` as an unknown key.

- [ ] **Step 3: Implement model validation and strict parsing**

  Add the exact dataclass field and validation:

  ```python
  @dataclass(frozen=True)
  class MetricsConfig:
      collectors: tuple[MetricKind, ...]
      minimum_emergency_service_fraction: float
      minimum_service_link_weight: float

      def __post_init__(self) -> None:
          # Retain existing collector and SLA validation.
          threshold = self.minimum_service_link_weight
          if (
              isinstance(threshold, bool)
              or not isinstance(threshold, (int, float))
              or not 0 <= threshold <= 1
          ):
              raise ValueError(
                  "minimum_service_link_weight must be a number between 0 and 1"
              )
  ```

  Require `minimum_service_link_weight` in `_parse_simulation`'s exact metrics
  key set. Pass `_require_number(...)` into `MetricsConfig` so YAML booleans
  are rejected and constructor failures become path-aware `ConfigurationError`
  values. Set the default YAML threshold to `0.0` to preserve the former
  positive-edge service behavior.

- [ ] **Step 4: Run focused configuration tests to verify they pass**

  Run: `uv run pytest tests/configuration/test_models.py tests/configuration/test_loader.py tests/test_simulation.py -v`

  Expected: PASS, including valid `0.0`, exact strict-schema errors, and all
  updated direct configuration fixtures.

- [ ] **Step 5: Commit the configuration change**

  ```bash
  git add src/simulator/configuration/models.py src/simulator/configuration/loader.py src/simulator/configuration/__init__.py configs/default.yaml tests/configuration/test_models.py tests/configuration/test_loader.py tests/test_simulation.py
  git commit -m "feat: configure minimum service link weight"
  ```

### Task 2: Enforce the served-user conditions in service-based collectors

**Files:**
- Modify: `src/simulator/metrics/service.py`
- Modify: `src/simulator/metrics/average_emergency_qos.py`
- Modify: `src/simulator/metrics/network_lifetime.py`
- Modify: `tests/metrics/conftest.py`
- Modify: `tests/metrics/test_service.py`
- Modify: `tests/metrics/test_average_emergency_qos.py`
- Modify: `tests/metrics/test_network_lifetime.py`

**Interfaces:**
- Produces `_served_user_fraction(environment: Environment, minimum_service_link_weight: float) -> float`.
- Produces `AverageEmergencyQoSCollector(minimum_service_link_weight: float)`.
- Produces `NetworkLifetimeCollector(minimum_emergency_service_fraction: float, minimum_service_link_weight: float)`.

- [ ] **Step 1: Write failing service and constructor tests**

  Upgrade `FakeEnvironment` so `get_connectivity_graph()` returns a NetworkX
  graph containing exactly the configured user-RU associations and their
  weights. Preserve its public `get_connection_weight()` behavior.

  Add exact service helper tests:

  ```python
  def test_rejects_edge_below_service_link_threshold() -> None:
      user = User(id=1)
      ru = make_ru(1, RUStatus.ACTIVE)
      environment = FakeEnvironment([user], [ru])
      environment.set_connection_weight(user, ru, 0.29)

      assert _served_user_fraction(environment, 0.3) == 0.0


  def test_accepts_edge_equal_to_service_link_threshold() -> None:
      user = User(id=1)
      ru = make_ru(1, RUStatus.ACTIVE)
      environment = FakeEnvironment([user], [ru])
      environment.set_connection_weight(user, ru, 0.3)

      assert _served_user_fraction(environment, 0.3) == 1.0


  def test_zero_threshold_does_not_accept_an_absent_edge() -> None:
      user = User(id=1)
      environment = FakeEnvironment([user], [make_ru(1, RUStatus.ACTIVE)])

      assert _served_user_fraction(environment, 0.0) == 0.0
  ```

  Add a test that drains an otherwise active RU to zero before collection and
  proves it does not serve the user. Add constructor tests rejecting `-0.1`,
  `1.1`, `True`, and a string for both service-based collectors.

- [ ] **Step 2: Run the focused metric tests to verify they fail**

  Run: `uv run pytest tests/metrics/test_service.py tests/metrics/test_average_emergency_qos.py tests/metrics/test_network_lifetime.py -v`

  Expected: FAIL because the helper and concrete collector constructors do not
  accept the service-link threshold and current service observation does not
  check battery or a distinct graph edge.

- [ ] **Step 3: Implement threshold-aware observation**

  In `service.py`, add one private threshold validator that rejects booleans,
  non-numbers, and values outside `[0, 1]`. Use it in both collector
  constructors and in the helper. Read the graph once per observation:

  ```python
  graph = environment.get_connectivity_graph()
  ```

  Count a user as served only with this predicate inside `any()`:

  ```python
  graph.has_edge(user, ru)
  and ru.get_status() is RUStatus.ACTIVE
  and ru.get_battery() > 0
  and environment.get_connection_weight(user, ru) >= minimum_service_link_weight
  ```

  Store `minimum_service_link_weight` as a public read-only-by-convention
  instance attribute on both service-based collectors so factory tests can
  inspect the exact configured value. Pass it to `_served_user_fraction()` from
  each collector's `_collect()` method. Do not change the battery-depletion
  collector.

- [ ] **Step 4: Run the focused metric tests to verify they pass**

  Run: `uv run pytest tests/metrics/test_service.py tests/metrics/test_average_emergency_qos.py tests/metrics/test_network_lifetime.py -v`

  Expected: PASS. The suite proves all four served-user conditions, equality,
  zero-threshold edge handling, direct validation, and threshold-sensitive
  QoS/lifetime results.

- [ ] **Step 5: Commit service observation changes**

  ```bash
  git add src/simulator/metrics/service.py src/simulator/metrics/average_emergency_qos.py src/simulator/metrics/network_lifetime.py tests/metrics/conftest.py tests/metrics/test_service.py tests/metrics/test_average_emergency_qos.py tests/metrics/test_network_lifetime.py
  git commit -m "feat: require service link quality"
  ```

### Task 3: Wire the configured threshold through the factory and document it

**Files:**
- Modify: `src/simulator/metrics/factories.py`
- Modify: `tests/metrics/test_factories.py`
- Modify: `README.md`

**Interfaces:**
- `build_metric_collectors(config: MetricsConfig) -> list[MetricCollector]` passes `config.minimum_service_link_weight` to only QoS and Network Lifetime collectors.

- [ ] **Step 1: Write failing factory tests**

  Update the factory configuration fixture with
  `minimum_service_link_weight=0.6`. Assert that the two service-based
  collectors retain it and the battery collector is still constructed without
  service parameters:

  ```python
  collectors = build_metric_collectors(
      MetricsConfig(
          collectors=(
              MetricKind.AVERAGE_EMERGENCY_QOS,
              MetricKind.AVERAGE_RU_BATTERY_DEPLETION_TIME,
              MetricKind.NETWORK_LIFETIME,
          ),
          minimum_emergency_service_fraction=0.8,
          minimum_service_link_weight=0.6,
      )
  )

  assert collectors[0].minimum_service_link_weight == 0.6
  assert isinstance(collectors[1], AverageRUBatteryDepletionTimeCollector)
  assert collectors[2].minimum_service_link_weight == 0.6
  ```

- [ ] **Step 2: Run the factory test to verify it fails**

  Run: `uv run pytest tests/metrics/test_factories.py -v`

  Expected: FAIL because the factory still constructs QoS without a threshold
  and passes only the SLA fraction to Network Lifetime.

- [ ] **Step 3: Implement factory wiring and README documentation**

  Pass `config.minimum_service_link_weight` into each service-based collector,
  preserving configuration order and the existing empty-list behavior. Update
  the README metrics YAML example to include the new key. State that service
  requires an existing graph edge, active RU, positive battery, and weight at
  least the threshold; document that `0.0` disables only the additional quality
  filter and still requires an edge.

- [ ] **Step 4: Run focused integration tests to verify they pass**

  Run: `uv run pytest tests/metrics/test_factories.py tests/metrics/test_service.py tests/metrics/test_average_emergency_qos.py tests/metrics/test_network_lifetime.py -v`

  Expected: PASS with the factory preserving the exact threshold and all
  threshold-serving semantics covered.

- [ ] **Step 5: Run complete verification and commit**

  Run:

  ```bash
  uv run pytest
  uv run ruff check .
  uv run ruff format --check .
  git diff --check HEAD
  ```

  Expected: all tests pass, both Ruff commands exit `0`, and the Git whitespace
  check reports no errors.

  Commit:

  ```bash
  git add src/simulator/metrics/factories.py tests/metrics/test_factories.py README.md
  git commit -m "docs: explain service link threshold"
  ```
