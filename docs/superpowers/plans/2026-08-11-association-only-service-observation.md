# Association-Only Service Observation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Count every accepted RU-user association as service without rechecking the associated RU's state.

**Architecture:** Environment association rebuilding remains the sole admission decision: it filters inactive, depleted, full, and below-threshold RUs immediately before metrics run. The shared service helper therefore counts only non-`None` association-map lookups; QoS and Network Lifetime retain their existing formulas through that helper.

**Tech Stack:** Python 3.12, pytest, Ruff, uv.

## Global Constraints

- Do not change environment association admission, battery charging, controller timing, configuration, or collector result formulas.
- Service metrics must remain read-only observers of the environment.
- Keep the empty-user `ValueError` contract.
- Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, and `git diff --check` before completion.

---

### Task 1: Count Accepted Associations Directly

**Files:**
- Modify: `src/simulator/metrics/service.py`
- Modify: `tests/metrics/test_service.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: `Environment.get_users() -> list[User]` and `Environment.get_associated_ru(user: User) -> RU | None`.
- Produces: `_served_user_fraction(environment: Environment) -> float`.
- Preserves: empty-user validation and all service collector APIs.

- [ ] **Step 1: Write failing association-only regressions**

  Change the sleeping and depleted association tests so both assert service,
  because the association map is now authoritative:

  ```python
  def test_sleeping_associated_ru_serves_a_user() -> None:
      user = User(id=1)
      ru = make_ru(1, RUStatus.SLEEP)
      environment = FakeEnvironment([user], [ru])
      environment.set_associated_ru(user, ru)

      assert _served_user_fraction(environment) == 1.0
  ```

  ```python
  def test_depleted_associated_ru_serves_a_user() -> None:
      user = User(id=1)
      ru = make_ru(1, RUStatus.ACTIVE)
      environment = FakeEnvironment([user], [ru])
      environment.set_associated_ru(user, ru)
      ru.update_battery(delta_time=10.0)

      assert _served_user_fraction(environment) == 1.0
  ```

  Keep the unassociated-user test asserting `0.0`.

- [ ] **Step 2: Run the sleeping association test to verify RED**

  Run:

  ```bash
  uv run pytest tests/metrics/test_service.py::test_sleeping_associated_ru_serves_a_user -v
  ```

  Expected: FAIL because the current helper still rejects an associated RU in
  `RUStatus.SLEEP`.

- [ ] **Step 3: Implement the minimal association-only count**

  Replace the served-count expression with:

  ```python
  served_user_count = sum(
      environment.get_associated_ru(user) is not None for user in users
  )
  ```

  Remove the now-unused `RUStatus` import. Do not add replacement status or
  battery checks elsewhere.

- [ ] **Step 4: Update the README metric description**

  State that an accepted association alone represents service for QoS and
  Network Lifetime. Keep the statement that the environment applies quality,
  availability, and capacity rules when associations are created.

- [ ] **Step 5: Verify focused behavior and commit**

  Run:

  ```bash
  uv run pytest tests/metrics/test_service.py -v
  uv run pytest tests/metrics -v
  uv run ruff check .
  uv run ruff format --check .
  git diff --check
  ```

  Expected: PASS. Associated users are served regardless of post-association
  RU state; unassociated users are not served.

  Commit:

  ```bash
  git add src/simulator/metrics/service.py tests/metrics/test_service.py README.md
  git commit -m "refactor: count accepted associations as service"
  ```

### Task 2: Run Repository-Wide Verification

**Files:**
- Verify only: repository-wide source and tests.

**Interfaces:**
- Confirms: service collectors continue to use `_served_user_fraction(environment)` and association admission remains the environment's only eligibility decision.

- [ ] **Step 1: Run the complete verification set**

  ```bash
  uv run pytest
  uv run ruff check .
  uv run ruff format --check .
  git diff --check
  ```

  Expected: all commands exit `0`.

- [ ] **Step 2: Inspect branch state**

  ```bash
  git status --short
  git diff --check HEAD
  ```

  Expected: no uncommitted changes and no whitespace errors.

## Plan Self-Review

- **Spec coverage:** Task 1 removes all post-admission RU state checks from the shared helper, updates behavior tests, and documents the resulting metric rule. Task 2 verifies the complete integration.
- **Placeholder scan:** Every change, expected failure, and verification command is explicit.
- **Type consistency:** The existing helper signature remains `_served_user_fraction(environment: Environment) -> float`; no collector or factory interface changes are needed.
