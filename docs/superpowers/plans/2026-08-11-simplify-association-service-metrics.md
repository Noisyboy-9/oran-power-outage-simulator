# Simplify Association Service Metrics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make accepted RU-user associations the sole connection-eligibility input for service metrics.

**Architecture:** The environment continues to apply `minimum_service_link_weight` while creating each timestep's association map. The shared service helper then needs only the environment: a user is served when its accepted RU exists, is active, and has battery. Service collectors no longer own an unused link-quality setting, while `MetricsConfig` retains the setting for environment admission.

**Tech Stack:** Python 3.12, pytest, Ruff, uv.

## Global Constraints

- Keep the connectivity graph and all link-quality checks in environment association admission; do not alter admission, battery charging, controller timing, or collector result formulas.
- Keep metric collectors observational: they must not mutate RU state, connectivity, or associations.
- Do not add dependencies or configuration fields.
- Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and `git diff --check` before completion.

---

### Task 1: Make the Shared Service Helper Trust Associations

**Files:**
- Modify: `src/simulator/metrics/service.py`
- Modify: `tests/metrics/test_service.py`

**Interfaces:**
- Consumes: `Environment.get_users() -> list[User]`, `Environment.get_associated_ru(user: User) -> RU | None`, `RU.get_status() -> RUStatus`, and `RU.get_battery() -> float`.
- Produces: `_served_user_fraction(environment: Environment) -> float`.
- Removes: the helper's `minimum_service_link_weight` argument, threshold validation, connectivity-graph lookup, and connection-weight lookup.

- [ ] **Step 1: Write failing helper tests for the association-only contract**

  Change all existing helper calls to use only the environment. Replace the below-threshold, threshold-equality, missing-edge, and invalid-threshold tests with this behavioral regression:

  ```python
  def test_active_associated_ru_serves_without_a_connection_graph_edge() -> None:
      user = User(id=1)
      ru = make_ru(1, RUStatus.ACTIVE)
      environment = FakeEnvironment([user], [ru])
      environment.set_associated_ru(user, ru)

      assert _served_user_fraction(environment) == 1.0
  ```

  Keep the existing unassociated, sleeping-associated, depleted-associated, and non-associated-alternative-RU cases, but call the helper with only `environment`.

- [ ] **Step 2: Run the focused helper test to verify RED**

  Run:

  ```bash
  uv run pytest tests/metrics/test_service.py::test_active_associated_ru_serves_without_a_connection_graph_edge -v
  ```

  Expected: FAIL because the helper still requires the removed threshold argument, or because it still rejects the association due to the missing graph edge.

- [ ] **Step 3: Implement the minimal association-only helper**

  Replace the helper with this shape, retaining only the empty-user guard:

  ```python
  def _served_user_fraction(environment: Environment) -> float:
      users = environment.get_users()
      if not users:
          raise ValueError("cannot calculate served-user fraction without users")
      served_user_count = sum(
          (associated_ru := environment.get_associated_ru(user)) is not None
          and associated_ru.get_status() is RUStatus.ACTIVE
          and associated_ru.get_battery() > 0
          for user in users
      )
      return served_user_count / len(users)
  ```

  Delete `_validate_minimum_service_link_weight()` from this module. Do not change the environment's threshold validation or association rebuild.

- [ ] **Step 4: Verify the service helper suite is green**

  Run:

  ```bash
  uv run pytest tests/metrics/test_service.py -v
  ```

  Expected: PASS. An active associated RU is served even without a graph edge; association, status, and battery still control service.

- [ ] **Step 5: Commit the helper change**

  ```bash
  git add src/simulator/metrics/service.py tests/metrics/test_service.py
  git commit -m "refactor: trust RU associations for service"
  ```

### Task 2: Remove Link-Threshold Ownership From Service Collectors

**Files:**
- Modify: `src/simulator/metrics/average_emergency_qos.py`
- Modify: `src/simulator/metrics/network_lifetime.py`
- Modify: `src/simulator/metrics/factories.py`
- Modify: `tests/metrics/test_average_emergency_qos.py`
- Modify: `tests/metrics/test_network_lifetime.py`
- Modify: `tests/metrics/test_factories.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: `_served_user_fraction(environment: Environment) -> float` from Task 1.
- Produces: `AverageEmergencyQoSCollector()` and `NetworkLifetimeCollector(minimum_emergency_service_fraction: float)`.
- Preserves: `MetricsConfig.minimum_service_link_weight` for environment admission and all QoS/network-lifetime result calculations.

- [ ] **Step 1: Write failing collector and factory API tests**

  Update collector tests to construct the QoS collector without arguments and the Network Lifetime collector with only `minimum_emergency_service_fraction`. Remove tests that reject a collector-level link threshold or expect a threshold to alter an observed fraction. Add these focused expectations:

  ```python
  def test_average_emergency_qos_uses_association_service() -> None:
      collector = AverageEmergencyQoSCollector()
      collector.collect(make_environment(2), 0)

      assert collector.finish_calculation() == 1.0
  ```

  ```python
  def test_network_lifetime_accepts_only_service_fraction() -> None:
      collector = NetworkLifetimeCollector(minimum_emergency_service_fraction=0.5)

      assert collector.minimum_emergency_service_fraction == 0.5
  ```

  In factory tests, retain `MetricsConfig.minimum_service_link_weight=0.6` but assert neither resulting service collector exposes `minimum_service_link_weight`.

- [ ] **Step 2: Run focused collector tests to verify RED**

  Run:

  ```bash
  uv run pytest tests/metrics/test_average_emergency_qos.py tests/metrics/test_network_lifetime.py tests/metrics/test_factories.py -v
  ```

  Expected: FAIL because service collector constructors still require `minimum_service_link_weight` and factory wiring still passes it.

- [ ] **Step 3: Remove unused collector threshold state and factory wiring**

  Make the minimal signature and call-site changes:

  ```python
  class AverageEmergencyQoSCollector(MetricCollector):
      def __init__(self) -> None:
          super().__init__()
          self._served_fractions: dict[int, float] = {}

      def _collect(self, environment: Environment, timestamp: int) -> None:
          self._served_fractions[timestamp] = _served_user_fraction(environment)
  ```

  ```python
  class NetworkLifetimeCollector(MetricCollector):
      def __init__(self, minimum_emergency_service_fraction: float) -> None:
          super().__init__()
          # retain the existing service-fraction validation
          self.minimum_emergency_service_fraction = minimum_emergency_service_fraction
          self._served_fractions: dict[int, float] = {}
  ```

  In `build_metric_collectors()`, call `AverageEmergencyQoSCollector()` and
  `NetworkLifetimeCollector(config.minimum_emergency_service_fraction)`. Do not
  remove `minimum_service_link_weight` from `MetricsConfig`: `Simulation` still
  passes it to `Environment` for association admission.

- [ ] **Step 4: Update README service terminology**

  Replace any statement that QoS or Network Lifetime requires a current graph
  link or rechecks link quality with wording that they require an accepted,
  active, charged association. State that `minimum_service_link_weight` is
  applied when associations are created.

- [ ] **Step 5: Verify focused metrics and commit**

  Run:

  ```bash
  uv run pytest tests/metrics -v
  uv run ruff check .
  uv run ruff format --check .
  git diff --check
  ```

  Expected: PASS. QoS and Network Lifetime preserve their formulas but use the
  association-only served fraction; the configuration threshold remains used by
  environment admission.

  Commit:

  ```bash
  git add src/simulator/metrics tests/metrics README.md
  git commit -m "refactor: remove metric link-threshold checks"
  ```

### Task 3: Run Repository-Wide Verification

**Files:**
- Verify only: repository-wide source and tests.

**Interfaces:**
- Confirms: Task 1 helper API and Task 2 collector API integrate with simulation configuration without changing association admission.

- [ ] **Step 1: Run the complete verification set**

  ```bash
  uv run pytest
  uv run ruff check .
  uv run ruff format --check .
  git diff --check
  ```

  Expected: all commands exit `0`.

- [ ] **Step 2: Inspect the final diff and commit status**

  ```bash
  git status --short
  git diff --check HEAD
  ```

  Expected: no uncommitted changes and no whitespace errors.

## Plan Self-Review

- **Spec coverage:** Task 1 makes the shared helper association-only. Task 2 removes the now-unused threshold collector API while retaining the configuration threshold for environment admission and documents the boundary. Task 3 validates the integrated repository.
- **Placeholder scan:** No deferred work or placeholder steps remain; every production and test change has a concrete signature or behavior.
- **Type consistency:** Task 1 produces `_served_user_fraction(environment)`. Task 2 changes both service collectors and their factory to use precisely that one-argument helper. `MetricsConfig.minimum_service_link_weight` is explicitly retained outside the collector API.
