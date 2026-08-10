# RU User-Load Battery Consumption Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace binary active/sleep RU battery depletion with active load-aware depletion based on qualifying RU-user links, while retaining sleep consumption and minimum-cost controller activation.

**Architecture:** `RU` remains the sole owner of consumption selection and battery mutation. `Simulation` passes the configured service-link threshold into `Environment.update()`, which counts qualifying edges in its current connectivity graph and supplies each RU's count before controller selection and graph rebuild. Controllers only use the zero-user rate as their activation minimum.

**Tech Stack:** Python 3.12, pytest, NetworkX, PyYAML, Ruff, uv.

## Global Constraints

- Remove `active_consumption`; do not retain compatibility aliases or accept the legacy YAML key.
- Required positive RU rates are `zero_user_consumption`, `one_user_consumption`, `multi_user_consumption_per_user`, and `sleep_consumption`.
- A qualifying user is any current graph edge for which `weight >= minimum_service_link_weight`; no user-to-RU association is introduced, so a user may count for multiple RUs.
- Sleeping RUs always use `sleep_consumption`, irrespective of qualifying-link count.
- Active RUs use zero-user, one-user, or `count * multi_user_consumption_per_user` consumption for counts 0, 1, and 2+ respectively.
- Preserve the update order: charge using the current graph/status, apply the controller, then rebuild the graph.
- Controllers activate at `battery >= zero_user_consumption`; a busy RU may deplete to zero and is slept by that same update's controller pass.
- Keep `minimum_service_link_weight` in `simulation.metrics` as the single configuration source.
- Do not add dependencies, assignment policies, or changes to metric definitions.

---

## File Structure

- Modify `src/simulator/domain/ru.py`: store and validate the replacement rates; calculate depletion from status and serviced-user count.
- Modify `src/simulator/environment/config.py`: expose and validate the replacement RU configuration fields.
- Modify `src/simulator/controllers/utils.py`: use the zero-user rate for activation eligibility and failure logging.
- Modify `src/simulator/environment/environment.py`: accept the service-link threshold during updates and count qualifying graph edges before battery charging.
- Modify `src/simulator/simulation.py`: forward its configured service-link threshold to every environment update.
- Modify `src/simulator/configuration/loader.py`: require, parse, and construct the replacement YAML fields.
- Modify `configs/default.yaml` and `README.md`: publish the new configuration defaults and timestep semantics.
- Modify domain, environment, controller, configuration, connectivity, simulation, and metric test fixtures that construct an `RU` or `RUConfig`.

### Task 1: Implement Load-Aware RU and RU Configuration

**Files:**
- Modify: `tests/domain/test_ru.py`
- Modify: `tests/environment/test_config.py`
- Modify: `src/simulator/domain/ru.py`
- Modify: `src/simulator/environment/config.py`

**Interfaces:**
- Produces: `RU(id, battery, status, zero_user_consumption, one_user_consumption, multi_user_consumption_per_user, sleep_consumption)`.
- Produces: `RU.update_battery(delta_time: float = 1.0, serviced_user_count: int = 0) -> None`.
- Produces: `RUConfig(..., zero_user_consumption: float, one_user_consumption: float, multi_user_consumption_per_user: float, sleep_consumption: float, ...)`.
- Consumed by: controller helpers in Task 2 and environment charging in Task 3.

- [ ] **Step 1: Write the failing domain and direct-configuration tests**

  Replace the `active_consumption` fixture value in `tests/domain/test_ru.py` with
  `zero_user_consumption=1.0`, `one_user_consumption=2.0`, and
  `multi_user_consumption_per_user=1.5`. Replace the active depletion test with
  this table-driven behavior test, add the sleep case, and add count validation:

  ```python
  @pytest.mark.parametrize(
      ("serviced_user_count", "expected_battery"),
      [(0, 9.0), (1, 8.0), (2, 7.0), (3, 5.5)],
  )
  def test_active_ru_consumption_depends_on_serviced_user_count(
      serviced_user_count: int, expected_battery: float
  ) -> None:
      ru = make_ru()

      ru.update_battery(serviced_user_count=serviced_user_count)

      assert ru.get_battery() == pytest.approx(expected_battery)


  def test_sleeping_ru_uses_sleep_consumption_regardless_of_serviced_users() -> None:
      ru = make_ru(status=RUStatus.SLEEP)

      ru.update_battery(serviced_user_count=3)

      assert ru.get_battery() == pytest.approx(9.5)


  @pytest.mark.parametrize("serviced_user_count", [-1, True, 1.5])
  def test_rejects_invalid_serviced_user_count(serviced_user_count: object) -> None:
      with pytest.raises(DomainValidationError, match="serviced_user_count"):
          make_ru().update_battery(serviced_user_count=serviced_user_count)  # type: ignore[arg-type]
  ```

  Extend the constructor-positive-field parametrization to cover all three new
  rates and remove `active_consumption`. Update `tests/environment/test_config.py`
  so `make_ru_config()` supplies the three fields. Add a direct-config test that
  parameterizes each new field with `0.0`, `-1.0`, `True`, and `"1"` and expects
  `EnvironmentValidationError` naming that field.

- [ ] **Step 2: Run the focused tests to verify they fail for the missing interface**

  Run: `uv run pytest tests/domain/test_ru.py tests/environment/test_config.py -v`

  Expected: failures because `RU` and `RUConfig` do not accept the replacement
  rate keywords; no test should fail because of a test syntax or import error.

- [ ] **Step 3: Implement the replacement rates and consumption selection**

  In `src/simulator/domain/ru.py`, replace `active_consumption` with the three
  rates in the constructor, include them in `positive_fields`, and store them as
  public attributes. Preserve `delta_time` as the first optional argument and
  validate the count before selecting consumption:

  ```python
  def update_battery(
      self, delta_time: float = 1.0, serviced_user_count: int = 0
  ) -> None:
      if (
          isinstance(serviced_user_count, bool)
          or not isinstance(serviced_user_count, int)
          or serviced_user_count < 0
      ):
          raise DomainValidationError("serviced_user_count must be a non-negative integer")

      if self._status is RUStatus.SLEEP:
          consumption = self.sleep_consumption
      elif serviced_user_count == 0:
          consumption = self.zero_user_consumption
      elif serviced_user_count == 1:
          consumption = self.one_user_consumption
      else:
          consumption = serviced_user_count * self.multi_user_consumption_per_user
      self._battery = max(0.0, self._battery - delta_time * consumption)
  ```

  In `src/simulator/environment/config.py`, add the same three float fields to
  `RUConfig` and call `_require_positive_number()` for each replacement active
  consumption field and `sleep_consumption` in `RUConfig.__post_init__`. Leave
  existing `initial_battery` validation in the RU constructor so the current
  environment-level error boundary remains unchanged.

- [ ] **Step 4: Run the focused tests to verify the new behavior passes**

  Run: `uv run pytest tests/domain/test_ru.py tests/environment/test_config.py -v`

  Expected: PASS, including battery values `9.0`, `8.0`, `7.0`, `5.5`, sleeping
  behavior, count validation, and direct RU configuration validation.

- [ ] **Step 5: Commit the domain/configuration unit**

  ```bash
  git add src/simulator/domain/ru.py src/simulator/environment/config.py tests/domain/test_ru.py tests/environment/test_config.py
  git commit -m "feat: add load-aware RU battery consumption"
  ```

### Task 2: Apply the Minimum-Cost Rule to Controllers

**Files:**
- Modify: `tests/controllers/test_always_active.py`
- Modify: `tests/controllers/test_staggered_active.py`
- Modify: `tests/controllers/test_threshold_staggered_active.py`
- Modify: `tests/domain/test_map_cell.py`
- Modify: `tests/domain/test_user.py`
- Modify: `tests/metrics/conftest.py`
- Modify: `tests/metrics/test_service.py`
- Modify: `src/simulator/controllers/utils.py`

**Interfaces:**
- Consumes: `RU.zero_user_consumption` from Task 1.
- Produces: controller eligibility based on `ru.get_battery() >= ru.zero_user_consumption`.
- Produces: `ru_activation_failed.required_battery` equal to `ru.zero_user_consumption`.
- Consumed by: all environment updates in Task 3.

- [ ] **Step 1: Write failing controller-boundary tests and migrate fixture constructors**

  Replace every `active_consumption` constructor argument in the listed tests
  with the three replacement rates. In `tests/controllers/test_always_active.py`,
  add this test to distinguish the minimum-cost rule from one-user eligibility:

  ```python
  def test_activates_ru_with_exactly_the_zero_user_consumption() -> None:
      ru = make_ru(
          battery=1.0,
          zero_user_consumption=1.0,
          one_user_consumption=2.0,
      )

      AlwaysActiveController().update([ru], timestamp=4)

      assert ru.get_status() is RUStatus.ACTIVE
  ```

  In the staggered-controller tests, make the exact and underpowered cases use
  `zero_user_consumption` rather than the removed active rate. Add an INFO-log
  regression test using `structlog.testing.capture_logs()` that updates a
  selected RU with battery `0.5` and `zero_user_consumption=1.0`, then asserts
  the captured `ru_activation_failed` event includes `required_battery == 1.0`.

- [ ] **Step 2: Run controller and dependent-fixture tests to verify expected failure**

  Run: `uv run pytest tests/controllers tests/domain/test_map_cell.py tests/domain/test_user.py tests/metrics -v`

  Expected: controller-boundary failures because eligibility still reads
  `active_consumption`, plus constructor failures from the removed keyword;
  address fixture-only constructor failures before judging the controller
  behavior failure.

- [ ] **Step 3: Change controller eligibility and all affected test fixtures**

  In `src/simulator/controllers/utils.py`, make both uses of the former field
  read `ru.zero_user_consumption`:

  ```python
  def _can_activate(ru: RU) -> bool:
      return ru.get_battery() >= ru.zero_user_consumption

  # inside the ru_activation_failed log event
  required_battery=ru.zero_user_consumption,
  ```

  Update every listed test helper and direct `RU(...)` call to provide
  `zero_user_consumption=1.0`, `one_user_consumption=2.0`, and
  `multi_user_consumption_per_user=1.5`, unless a test intentionally uses a
  different zero-user boundary. Update `drain_to()` in the threshold-controller
  test to divide by `ru.zero_user_consumption` and call
  `ru.update_battery(delta_time=delta_time, serviced_user_count=0)`.

- [ ] **Step 4: Run the controller and dependent-fixture tests to verify they pass**

  Run: `uv run pytest tests/controllers tests/domain/test_map_cell.py tests/domain/test_user.py tests/metrics -v`

  Expected: PASS. The new activation-boundary test proves a battery of `1.0`
  activates even when the one-user rate is `2.0`; the capture-logs test reports
  the zero-user requirement.

- [ ] **Step 5: Commit the controller migration**

  ```bash
  git add src/simulator/controllers/utils.py tests/controllers tests/domain/test_map_cell.py tests/domain/test_user.py tests/metrics
  git commit -m "feat: use minimum active cost for RU activation"
  ```

### Task 3: Count Qualifying Links During Environment Updates

**Files:**
- Modify: `tests/environment/test_environment.py`
- Modify: `tests/environment/test_connectivity.py`
- Modify: `tests/test_simulation.py`
- Modify: `src/simulator/environment/environment.py`
- Modify: `src/simulator/simulation.py`

**Interfaces:**
- Consumes: `Environment.update(timestamp: int, minimum_service_link_weight: float)`.
- Consumes: `RU.update_battery(serviced_user_count=...)` from Task 1.
- Produces: battery charging from current qualifying graph edges before controller selection.
- Consumed by: `Simulation._step()` and direct environment-update callers.

- [ ] **Step 1: Write failing graph-load and threshold-forwarding tests**

  Update all direct `Environment.update()` calls to supply a threshold. In
  `tests/environment/test_environment.py`, add a helper that replaces the
  environment's private graph with a controlled `nx.Graph` containing all owned
  nodes and explicit RU-user edge weights. Then add this integration test:

  ```python
  def test_update_charges_an_active_ru_for_only_qualifying_current_links() -> None:
      environment = Environment(
          make_config(
              ru_count=1,
              user_count=3,
              initial_battery=10.0,
              zero_user_consumption=1.0,
              one_user_consumption=2.0,
              multi_user_consumption_per_user=1.5,
          ),
          RecordingController(),
      )
      ru = environment.get_rus()[0]
      users = environment.get_users()
      controlled_graph = nx.Graph()
      controlled_graph.add_nodes_from([ru, *users])
      controlled_graph.add_edge(ru, users[0], weight=0.6)
      controlled_graph.add_edge(ru, users[1], weight=0.8)
      controlled_graph.add_edge(ru, users[2], weight=0.5)
      environment._connectivity_graph = controlled_graph

      environment.update(timestamp=1, minimum_service_link_weight=0.6)

      assert ru.get_battery() == pytest.approx(7.0)
  ```

  This asserts that equality qualifies, the below-threshold edge does not, and
  two qualifying users consume `2 * 1.5`. Add a zero-qualifying-link test that
  expects `9.0`. In `tests/test_simulation.py`, change `RecordingEnvironment`
  to record `update(timestamp, minimum_service_link_weight)` and assert that a
  simulation configured with `0.0` forwards `0.0` for each step.

- [ ] **Step 2: Run the focused environment and simulation tests to verify they fail**

  Run: `uv run pytest tests/environment/test_environment.py tests/environment/test_connectivity.py tests/test_simulation.py -v`

  Expected: failures because `Environment.update()` accepts only a timestamp and
  `Simulation._step()` does not supply a service-link threshold.

- [ ] **Step 3: Implement current-graph serviced-user counting and forwarding**

  Change `Environment.update()` and `_update_batteries()` to accept the
  threshold. Add a private counting helper that only counts owned users with an
  existing edge at or above the threshold, then charge each RU before the
  controller update:

  ```python
  def _serviced_user_count(self, ru: RU, minimum_service_link_weight: float) -> int:
      return sum(
          1
          for user in self._users
          if (edge := self._connectivity_graph.get_edge_data(ru, user)) is not None
          and edge["weight"] >= minimum_service_link_weight
      )

  def _update_batteries(self, minimum_service_link_weight: float) -> None:
      for ru in self._rus:
          ru.update_battery(
              serviced_user_count=self._serviced_user_count(
                  ru, minimum_service_link_weight
              )
          )
  ```

  Preserve the existing order in `update()`:

  ```python
  self._update_batteries(minimum_service_link_weight)
  self._rus = self._controller.update(self.get_rus(), timestamp).copy()
  self._update_connectivity_graph()
  ```

  In `Simulation._step()`, pass
  `self._config.simulation.metrics.minimum_service_link_weight` as the second
  argument to `self._environment.update()`. Update the simulation fixture to
  use the replacement rates and change its final battery assertions from `6.0`
  to `7.0`: the first step charges sleep by `1.0`, and the second charges one
  qualifying user by `2.0`.

- [ ] **Step 4: Run the focused environment and simulation tests to verify they pass**

  Run: `uv run pytest tests/environment/test_environment.py tests/environment/test_connectivity.py tests/test_simulation.py -v`

  Expected: PASS. The controlled graph proves the exact threshold boundary and
  two-user multiplication; the lifecycle test proves the threshold is supplied
  before collector observation.

- [ ] **Step 5: Commit the environment/simulation integration**

  ```bash
  git add src/simulator/environment/environment.py src/simulator/simulation.py tests/environment/test_environment.py tests/environment/test_connectivity.py tests/test_simulation.py
  git commit -m "feat: charge RUs by qualifying user links"
  ```

### Task 4: Load the New YAML Schema and Document the Model

**Files:**
- Modify: `tests/configuration/test_loader.py`
- Modify: `tests/configuration/test_factories.py`
- Modify: `tests/test_main.py`
- Modify: `src/simulator/configuration/loader.py`
- Modify: `configs/default.yaml`
- Modify: `README.md`

**Interfaces:**
- Consumes: new `RUConfig` fields from Task 1.
- Produces: YAML configuration that uses and exposes only the replacement rates.
- Produces: user documentation consistent with the step implementation in Task 3.

- [ ] **Step 1: Write failing YAML schema and default-value tests**

  In `tests/configuration/test_loader.py`, replace the `active_consumption` line
  in `VALID_YAML` with:

  ```yaml
    zero_user_consumption: 1.0
    one_user_consumption: 2.0
    multi_user_consumption_per_user: 1.5
  ```

  Extend `test_loads_typed_configuration()` to assert all three values. Add
  parameterized invalid cases replacing each field with `false`, `0`, and `-1`,
  expecting that exact `environment.ru.<field>` path. Add a case that restores
  `active_consumption: 2.0` in place of the three new fields and expects
  `environment.ru.active_consumption: unknown key`. Update every `RUConfig` fixture in
  `tests/configuration/test_factories.py` and `tests/test_main.py` to use the
  replacement rates.

- [ ] **Step 2: Run the configuration and entry-point tests to verify they fail**

  Run: `uv run pytest tests/configuration tests/test_main.py -v`

  Expected: YAML loading rejects the new keys as unknown and requires the legacy
  key, demonstrating that the parser has not yet been migrated.

- [ ] **Step 3: Implement parser migration, defaults, and documentation**

  In `_parse_environment()` in `src/simulator/configuration/loader.py`, replace
  `active_consumption` in the exact expected RU-key set with the three new keys
  and construct `RUConfig` using `_require_positive_number()` for each one:

  ```python
  zero_user_consumption=_require_positive_number(
      raw_ru["zero_user_consumption"],
      _join_path(ru_path, "zero_user_consumption"),
  ),
  one_user_consumption=_require_positive_number(
      raw_ru["one_user_consumption"],
      _join_path(ru_path, "one_user_consumption"),
  ),
  multi_user_consumption_per_user=_require_positive_number(
      raw_ru["multi_user_consumption_per_user"],
      _join_path(ru_path, "multi_user_consumption_per_user"),
  ),
  ```

  Put the approved defaults `1.0`, `2.0`, and `1.5` in `configs/default.yaml`.
  In `README.md`, replace active/sleep terminology in the Domain Models,
  `RUConfig` example, controller eligibility description, and simulation-step
  ordering text with the three active load rates, qualifying links at the
  configured minimum service-link weight, and zero-user controller eligibility.
  State explicitly that qualifying users may be counted by multiple RUs because
  the simulator has no association policy.

- [ ] **Step 4: Run configuration, entry-point, and documentation-adjacent tests**

  Run: `uv run pytest tests/configuration tests/test_main.py -v`

  Expected: PASS, including tracked-default configuration loading and exact
  validation paths for all three new fields.

- [ ] **Step 5: Run full verification and commit the completed feature**

  Run:

  ```bash
  uv run pytest
  uv run ruff check .
  uv run ruff format --check .
  git diff --check
  ```

  Expected: every command exits `0` with no test failures, lint violations,
  formatting changes, or whitespace errors.

  Commit:

  ```bash
  git add src/simulator/configuration/loader.py configs/default.yaml README.md tests/configuration tests/test_main.py
  git commit -m "feat: configure RU user-load battery rates"
  ```
