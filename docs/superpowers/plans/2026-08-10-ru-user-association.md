# RU–User Association Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make each user associate with at most one active, battery-powered RU that meets the configured minimum link quality and has remaining user capacity.

**Architecture:** Keep the existing weighted connectivity graph as the complete set of possible links. `Environment` owns a separate private `User -> RU | None` mapping for actual admissions, rebuilds it from the current graph after construction and after every update, and exposes only an identity-safe lookup. Battery charging and service metrics consume that mapping rather than treating every qualifying graph edge as an active service relationship.

**Tech Stack:** Python 3.12, pytest, NetworkX, PyYAML, Ruff, uv.

## Global Constraints

- Preserve the merged load-aware RU rates: `zero_user_consumption`, `one_user_consumption`, `multi_user_consumption_per_user`, and `sleep_consumption`.
- Add required positive integer `user_capacity` uniformly to `RUConfig` and `RU`; zero, negatives, booleans, and non-integers are invalid.
- Keep one weighted connectivity graph for possible in-range links; do not add an association graph.
- The existing inclusive `minimum_service_link_weight` is the single service-quality and association-admission threshold.
- A candidate with weight below the threshold is never contacted; candidates are ranked by descending weight and then ascending RU ID.
- Skip sleeping or battery-depleted candidates. A full RU rejects the request, and the user tries the next qualifying candidate.
- Rebuild the entire association mapping at construction and after every connectivity-graph rebuild; preserve no session or handover state.
- Charge each RU from the prior association mapping, then run the controller, rebuild the connectivity graph, and rebuild associations.
- QoS and Network Lifetime continue using their existing formulas; only their shared service observation changes. Battery-depletion metrics remain association-agnostic.
- Add no dependencies or new configuration sections.

---

## File Structure

- `src/simulator/domain/ru.py`: stores an RU's immutable user capacity.
- `src/simulator/environment/config.py`: validates the uniform capacity setting.
- `src/simulator/configuration/loader.py`: requires and parses `environment.ru.user_capacity`.
- `src/simulator/environment/environment.py`: owns association state, admission, capacity accounting, initial association construction, update-time reassociation, and association-based load counting.
- `src/simulator/simulation.py`: supplies the existing configured threshold when constructing `Environment`.
- `src/simulator/metrics/service.py`: derives service from an association rather than any candidate RU.
- `tests/domain/test_ru.py`, `tests/environment/test_config.py`, `tests/configuration/test_loader.py`: cover capacity storage and validation.
- `tests/environment/test_environment.py`, `tests/environment/test_connectivity.py`, `tests/test_simulation.py`: cover association allocation, lifecycle timing, and threshold handoff.
- `tests/metrics/conftest.py`, `tests/metrics/test_service.py`, `tests/metrics/test_average_emergency_qos.py`, `tests/metrics/test_network_lifetime.py`: make metric test environments association-aware and cover the new service semantics.
- Existing test helpers that construct `RU` or `RUConfig`: supply `user_capacity=100` unless a test needs a smaller capacity.
- `configs/default.yaml` and `README.md`: publish the new setting and the distinction between possible links and actual associations.

### Task 1: Add Uniform RU User Capacity

**Files:**
- Modify: `src/simulator/domain/ru.py`
- Modify: `src/simulator/environment/config.py`
- Modify: `src/simulator/configuration/loader.py`
- Modify: `configs/default.yaml`
- Modify: `tests/domain/test_ru.py`
- Modify: `tests/environment/test_config.py`
- Modify: `tests/configuration/test_loader.py`
- Modify: `tests/environment/test_environment.py`, `tests/environment/test_connectivity.py`, `tests/test_simulation.py`
- Modify: `tests/domain/test_map_cell.py`, `tests/controllers/test_always_active.py`, `tests/controllers/test_staggered_active.py`, `tests/controllers/test_threshold_staggered_active.py`, `tests/metrics/conftest.py`, and `tests/metrics/test_average_ru_battery_depletion_time.py`

**Interfaces:**
- Produces: `RU(..., user_capacity: int)` with public read-only-by-convention `user_capacity`.
- Produces: `RUConfig(..., user_capacity: int, ...)`.
- Produces: YAML key `environment.ru.user_capacity`.
- Consumed by: environment admission in Task 2.

- [ ] **Step 1: Write the failing capacity tests and migrate fixture signatures**

  Add `"user_capacity": 100` to `tests/domain/test_ru.py`'s `make_ru()` values and assert it is exposed:

  ```python
  def test_exposes_battery_initial_capacity_and_user_capacity() -> None:
      ru = make_ru(battery=12.0, user_capacity=3)

      assert ru.get_battery() == 12.0
      assert ru.get_initial_capacity() == 12.0
      assert ru.user_capacity == 3
  ```

  Add this direct configuration validation in `tests/environment/test_config.py`:

  ```python
  @pytest.mark.parametrize("user_capacity", [0, -1, 1.5, True, "100"])
  def test_rejects_invalid_ru_user_capacity(user_capacity: object) -> None:
      with pytest.raises(EnvironmentValidationError, match="user_capacity"):
          make_ru_config(user_capacity=user_capacity)
  ```

  Add `user_capacity: 100` to `VALID_YAML` in
  `tests/configuration/test_loader.py`, assert the parsed value is `100`, and
  parameterize missing, `false`, `0`, `-1`, and an unknown `capacity` key with
  expected paths `environment.ru.user_capacity` and
  `environment.ru.capacity`.

  Extend `test_loads_tracked_default_configuration()` with:

  ```python
  assert config.environment.ru.user_capacity == 100
  ```

  Add `user_capacity=100` to every existing direct `RU(...)` and `RUConfig(...)`
  test construction listed in this task so the suite remains focused on the
  intended missing interface instead of unrelated constructor errors.

- [ ] **Step 2: Run the focused tests and verify they fail for the new field**

  Run:

  ```bash
  uv run pytest tests/domain/test_ru.py tests/environment/test_config.py tests/configuration/test_loader.py -v
  ```

  Expected: failures report that `RU` and `RUConfig` do not accept
  `user_capacity`, and the YAML loader rejects it as unknown.

- [ ] **Step 3: Implement capacity storage, validation, and parsing**

  Add `user_capacity: int` after `sleep_consumption` in `RU.__init__()`, reject
  invalid values explicitly, and store it:

  ```python
  if (
      isinstance(user_capacity, bool)
      or not isinstance(user_capacity, int)
      or user_capacity <= 0
  ):
      raise DomainValidationError("user_capacity must be a positive integer")
  self.user_capacity = user_capacity
  ```

  Add the same field to `RUConfig`, validate it with
  `_require_positive_integer("user_capacity", self.user_capacity)`, pass it
  when `Environment._create_rus()` constructs each RU, and require it in the
  loader's exact RU key set:

  ```python
  user_capacity=_require_positive_integer(
      raw_ru["user_capacity"],
      _join_path(ru_path, "user_capacity"),
  )
  ```

  Put `user_capacity: 100` in `configs/default.yaml` beside the other RU
  settings.

- [ ] **Step 4: Run the focused tests and verify the capacity interface passes**

  Run:

  ```bash
  uv run pytest tests/domain/test_ru.py tests/environment/test_config.py tests/configuration/test_loader.py -v
  ```

  Expected: PASS, including all invalid-value and YAML-path cases.

- [ ] **Step 5: Commit the capacity foundation**

  ```bash
  git add src/simulator/domain/ru.py src/simulator/environment/config.py src/simulator/configuration/loader.py configs/default.yaml tests
  git commit -m "feat: add RU user capacity"
  ```

### Task 2: Build and Rebuild Exclusive Associations

**Files:**
- Modify: `src/simulator/environment/environment.py`
- Modify: `src/simulator/simulation.py`
- Modify: `tests/environment/test_environment.py`
- Modify: `tests/environment/test_connectivity.py`
- Modify: `tests/test_simulation.py`

**Interfaces:**
- Consumes: `RU.user_capacity`, `RUStatus`, and `minimum_service_link_weight: float`.
- Produces: `Environment(config, controller, minimum_service_link_weight)`.
- Produces: `Environment.get_associated_ru(user: User) -> RU | None`.
- Produces: a private complete `dict[User, RU | None]` association mapping.
- Consumed by: Task 3's battery counting and Task 4's service helper.

- [ ] **Step 1: Write failing environment and simulation tests for admissions**

  Extend the environment fixture constructor to accept
  `minimum_service_link_weight: float = 0.0`. Add a test helper that replaces
  `_connectivity_graph`, invokes the private association rebuild with a
  threshold, and asserts through `get_associated_ru()`.

  Add tests equivalent to:

  ```python
  def test_associates_a_user_with_the_highest_weight_qualifying_ru() -> None:
      environment = Environment(
          make_config(ru_count=2, user_count=1, user_capacity=1),
          RecordingController(),
          minimum_service_link_weight=0.6,
      )
      first_ru, second_ru = environment.get_rus()
      user = environment.get_users()[0]
      replace_connectivity_graph(
          environment, [(first_ru, user, 0.6), (second_ru, user, 0.8)]
      )

      environment._update_associations(0.6)

      assert environment.get_associated_ru(user) is second_ru
  ```

  Cover a below-threshold best-looking edge that is not contacted, equality at
  the threshold, a full first RU falling back to the next candidate, all
  candidates full producing `None`, sleeping and depleted candidates producing
  `None`, one RU never receiving more than its capacity, ties choosing the
  lower RU ID, and a foreign equal-ID user returning `None`.

  Add an integration test that constructs an initially sleeping RU with a
  threshold of `0.0`, runs an always-active update, and verifies associations
  are rebuilt after the controller has activated the RU. Update the simulation
  monkeypatch fixture so its fake `Environment` constructor records the third
  threshold argument and asserts that it equals the configured metric threshold
  before the collector receives timestamp zero. Update every direct
  `Environment(...)` construction in the listed environment and connectivity
  tests to pass a threshold, using `0.0` except where the test exercises a
  quality boundary.

- [ ] **Step 2: Run the focused tests and verify the association API is missing**

  Run:

  ```bash
  uv run pytest tests/environment/test_environment.py tests/environment/test_connectivity.py tests/test_simulation.py -v
  ```

  Expected: failures report the unsupported third `Environment` constructor
  argument and missing `get_associated_ru` or `_update_associations` methods.

- [ ] **Step 3: Implement a mapping, quality-filtered admission, and lifecycle hooks**

  Import `RUStatus`. Accept the threshold as the third `Environment`
  constructor argument, create the graph, then create the mapping before the
  constructor returns:

  ```python
  self._connectivity_graph = self._create_connectivity_graph()
  self._user_associations: dict[User, RU | None] = {}
  self._update_associations(minimum_service_link_weight)
  ```

  Implement the rebuild as a fresh mapping with explicit identity-preserving RU
  instances:

  ```python
  def _update_associations(self, minimum_service_link_weight: float) -> None:
      accepted_user_counts = {ru: 0 for ru in self._rus}
      associations: dict[User, RU | None] = {}
      for user in sorted(self._users, key=lambda candidate: candidate.id):
          candidates = sorted(
              (
                  (ru, float(edge["weight"]))
                  for ru in self._rus
                  if (edge := self._connectivity_graph.get_edge_data(user, ru))
                  is not None
                  and edge["weight"] >= minimum_service_link_weight
              ),
              key=lambda candidate: (-candidate[1], candidate[0].id),
          )
          associated_ru = None
          for ru, _weight in candidates:
              if ru.get_status() is RUStatus.SLEEP or ru.get_battery() <= 0:
                  continue
              if accepted_user_counts[ru] >= ru.user_capacity:
                  continue
              associated_ru = ru
              accepted_user_counts[ru] += 1
              break
          associations[user] = associated_ru
      self._user_associations = associations
  ```

  Add `get_associated_ru()` with the same object-identity ownership check used
  by `get_connection_weight()`.

  After `_update_connectivity_graph()` in `Environment.update()`, call
  `_update_associations(minimum_service_link_weight)`. Change `Simulation` to
  pass `config.simulation.metrics.minimum_service_link_weight` into the
  `Environment` constructor.

- [ ] **Step 4: Run the focused tests and verify association behavior passes**

  Run:

  ```bash
  uv run pytest tests/environment/test_environment.py tests/environment/test_connectivity.py tests/test_simulation.py -v
  ```

  Expected: PASS. The tests prove threshold filtering, ranked fallback,
  capacities, availability exclusion, deterministic ties, initial construction,
  and post-controller reassociation.

- [ ] **Step 5: Commit association lifecycle support**

  ```bash
  git add src/simulator/environment/environment.py src/simulator/simulation.py tests/environment tests/test_simulation.py
  git commit -m "feat: associate users with available RUs"
  ```

### Task 3: Charge RUs from Prior Associations

**Files:**
- Modify: `src/simulator/environment/environment.py`
- Modify: `tests/environment/test_environment.py`

**Interfaces:**
- Consumes: prior `Environment._user_associations` from Task 2.
- Produces: `serviced_user_count` equal to the number of users associated with
  the specific RU before controller selection.
- Consumed by: the existing `RU.update_battery(serviced_user_count=...)`.

- [ ] **Step 1: Write failing tests that distinguish associations from graph edges**

  Add a controlled graph with two active RUs and one user connected to both
  above the threshold. Rebuild associations so the user selects the
  higher-weight RU, run `Environment.update()`, and assert only that selected
  RU uses `one_user_consumption`; the other uses `zero_user_consumption`.

  Add a capacity test with two users associated to separate RUs and verify each
  RU receives exactly one-user consumption. These tests must not infer load
  from graph-edge degree.

- [ ] **Step 2: Run the environment tests and verify the graph-edge counting failure**

  Run:

  ```bash
  uv run pytest tests/environment/test_environment.py -v
  ```

  Expected: the unselected RU is incorrectly charged for the user's qualifying
  graph edge because `_serviced_user_count()` still iterates all users and
  checks graph edges.

- [ ] **Step 3: Replace graph-edge load counting with association counting**

  Replace the current helper with identity-based counting:

  ```python
  def _serviced_user_count(self, ru: RU) -> int:
      return sum(associated_ru is ru for associated_ru in self._user_associations.values())
  ```

  Remove the threshold parameter from this helper and from `_update_batteries()`
  because every association has already passed the threshold at admission.
  Keep `Environment.update(timestamp, minimum_service_link_weight)` unchanged:
  it still needs the threshold to build next-state associations after the graph
  rebuild.

- [ ] **Step 4: Run the environment tests and verify association-based charging passes**

  Run:

  ```bash
  uv run pytest tests/environment/test_environment.py -v
  ```

  Expected: PASS. Only the admitted RU incurs user load; all other active RUs
  use their zero-user rate.

- [ ] **Step 5: Commit association-based load accounting**

  ```bash
  git add src/simulator/environment/environment.py tests/environment/test_environment.py
  git commit -m "feat: charge RUs for associated users"
  ```

### Task 4: Make Service Observation Association-Aware

**Files:**
- Modify: `src/simulator/metrics/service.py`
- Modify: `tests/metrics/conftest.py`
- Modify: `tests/metrics/test_service.py`
- Modify: `tests/metrics/test_average_emergency_qos.py`
- Modify: `tests/metrics/test_network_lifetime.py`

**Interfaces:**
- Consumes: `Environment.get_associated_ru(user) -> RU | None` from Task 2.
- Produces: `_served_user_fraction()` based only on each user's accepted RU.
- Preserves: existing collector constructors, result formulas, and the
  association-independent battery-depletion collector.

- [ ] **Step 1: Write failing service and collector tests with explicit associations**

  Extend `FakeEnvironment` with `_associations: dict[User, RU | None]`,
  `set_associated_ru(user, ru) -> None`, and
  `get_associated_ru(user) -> RU | None`. Make all existing helper-produced
  served users call both `set_connection_weight()` and `set_associated_ru()`.

  Add this regression test:

  ```python
  def test_qualifying_non_associated_ru_does_not_serve_a_user() -> None:
      user = User(id=1)
      associated_ru = make_ru(1, RUStatus.SLEEP)
      alternative_ru = make_ru(2, RUStatus.ACTIVE)
      environment = FakeEnvironment([user], [associated_ru, alternative_ru])
      environment.set_connection_weight(user, associated_ru, 0.8)
      environment.set_connection_weight(user, alternative_ru, 0.9)
      environment.set_associated_ru(user, associated_ru)

      assert _served_user_fraction(environment, 0.6) == 0.0
  ```

  Also test an unassociated user with a valid edge, an associated edge exactly
  at threshold, and mutation snapshots that include `_associations`. Add one
  QoS and one Network Lifetime observation where a valid non-associated edge
  yields zero served fraction, proving both collectors inherit the shared
  helper.

- [ ] **Step 2: Run the metric tests and verify they fail for the missing lookup**

  Run:

  ```bash
  uv run pytest tests/metrics -v
  ```

  Expected: failures report that `FakeEnvironment` has no
  `get_associated_ru()` method, or the legacy any-RU implementation reports an
  incorrectly served user.

- [ ] **Step 3: Implement one-RU service observation**

  Replace the inner `any(...)` search in `_served_user_fraction()` with a
  single association lookup per user:

  ```python
  served_user_count = sum(
      (associated_ru := environment.get_associated_ru(user)) is not None
      and graph.has_edge(user, associated_ru)
      and associated_ru.get_status() is RUStatus.ACTIVE
      and associated_ru.get_battery() > 0
      and environment.get_connection_weight(user, associated_ru)
      >= minimum_service_link_weight
      for user in users
  )
  ```

  Keep the graph-edge check so a `0.0` threshold never accepts the missing-edge
  sentinel. Do not modify the QoS, Network Lifetime, battery-depletion, or
  factory production modules.

- [ ] **Step 4: Run the metric tests and verify the collectors pass**

  Run:

  ```bash
  uv run pytest tests/metrics -v
  ```

  Expected: PASS. QoS and Network Lifetime use only accepted RUs; the
  battery-depletion collector remains unaffected.

- [ ] **Step 5: Commit association-aware metrics**

  ```bash
  git add src/simulator/metrics/service.py tests/metrics
  git commit -m "feat: measure service through RU associations"
  ```

### Task 5: Document the Final Model and Verify the Repository

**Files:**
- Modify: `README.md`

**Interfaces:**
- Documents: `user_capacity`, one possible-link graph, one actual-association
  map, quality-filtered admission, association-based load, and association-based
  service.

- [ ] **Step 1: Update README terminology and examples**

  Add `user_capacity=100` to the `RUConfig` example. Explain that the
  connectivity graph contains every in-range weighted possibility, while the
  environment-owned association map contains one accepted RU or `None` per
  user. Replace the simulation claim that qualifying users can be counted by
  multiple RUs with these ordered operations: charge prior associations, apply
  the controller, rebuild possible links, rebuild associations, collect
  metrics. State that below-threshold RUs are never contacted and that QoS and
  Network Lifetime require the associated RU's valid current link.

- [ ] **Step 2: Run the complete verification set**

  Run:

  ```bash
  uv run pytest
  uv run ruff check .
  uv run ruff format --check .
  git diff --check
  ```

  Expected: all commands exit `0`; pytest includes the new capacity,
  association, load, metric, and configuration coverage.

- [ ] **Step 3: Commit documentation and final verification changes**

  ```bash
  git add README.md
  git commit -m "docs: describe RU user associations"
  ```

## Plan Self-Review

- **Spec coverage:** Task 1 implements uniform capacity and schema validation.
  Task 2 implements the one-map admission model, inclusive threshold filtering,
  availability, deterministic ordering, initial association, and every-step
  reassociation. Task 3 makes battery load exclusive. Task 4 makes service
  exclusive without altering collector formulas. Task 5 documents the model
  and runs all required checks.
- **Placeholder scan:** The plan contains no deferred implementation markers;
  every task gives concrete files, interfaces, tests, commands, and code shape.
- **Type consistency:** All later tasks use the Task 2 public lookup
  `get_associated_ru(user: User) -> RU | None`; Task 3 deliberately retains
  `Environment.update(timestamp, minimum_service_link_weight)` because Task 2
  uses its threshold for next-state admission.
