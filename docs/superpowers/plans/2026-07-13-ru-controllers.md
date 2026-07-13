# RU Controllers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Encapsulate RU battery and status state and implement always-active, timestamp-staggered, and battery-threshold-staggered RU controllers.

**Architecture:** `RU` owns its private mutable state and exposes explicit read/status-update methods. Three independent controller classes implement one abstract `update(rus, timestamp)` interface, with small shared helpers for timestamp validation, activation eligibility, and staggered parity selection. Standard-library module loggers record selected-but-ineligible RUs in the two staggered policies.

**Tech Stack:** Python 3.12, standard-library `abc`, `enum`, and `logging`; pytest; Ruff; uv.

## Global Constraints

- Keep domain objects independent of orchestration and infrastructure concerns.
- Controllers may depend on domain objects but must not own the complete environment or retain the RU collection.
- Controllers change RU statuses but never consume or replace battery.
- An RU is activation-eligible exactly when `current battery >= active consumption`.
- Staggered groups alternate every ten global timestamps without resetting.
- Threshold mode starts only when every RU is at or below the configured percentage and never exits.
- Use only Python's standard-library logger at `INFO`; add no dependency or logging abstraction.
- Preserve Python `>=3.12`, the existing constructor signature, and unrelated user changes.
- Use `uv run` for all tests, lint, and formatting checks.

---

## File Map

- Modify `src/simulator/domain/ru.py`: privately store battery, initial capacity, and status; expose the approved access methods.
- Modify `tests/domain/test_ru.py`: migrate existing assertions and cover state encapsulation and status validation.
- Modify `src/simulator/controllers/base.py`: define `RUController` and the small policy-neutral helpers.
- Modify `src/simulator/controllers/always_active.py`: implement the always-active policy.
- Create `tests/controllers/test_always_active.py`: cover the common interface, eligibility, no-op, and timestamp validation.
- Modify `src/simulator/controllers/staggered_active.py`: implement global timestamp parity and informational logging.
- Create `tests/controllers/test_staggered_active.py`: cover group boundaries, insufficient battery, and logging.
- Modify `src/simulator/controllers/threshold_staggered_active.py`: implement threshold validation and the permanent transition.
- Create `tests/controllers/test_threshold_staggered_active.py`: cover pre-threshold behavior, transition conditions, global timing, permanence, and logs.
- Modify `src/simulator/controllers/__init__.py`: expose the controller public API.
- Create `tests/controllers/test_public_imports.py`: verify the supported imports.
- Modify `README.md`: report the newly implemented controller behavior and RU access model.

---

### Task 1: Encapsulate RU Battery and Status State

**Files:**
- Modify: `tests/domain/test_ru.py`
- Modify: `src/simulator/domain/ru.py`

**Interfaces:**
- Consumes: existing `RUStatus`, `DomainValidationError`, and the current `RU(id, battery, status, active_consumption, sleep_consumption)` constructor.
- Produces: `RU.get_battery() -> float`, `RU.get_initial_capacity() -> float`, `RU.get_status() -> RUStatus`, `RU.set_status(status: RUStatus) -> None`, and unchanged `RU.update_battery(delta_time: float = 1.0) -> None`.

- [ ] **Step 1: Replace direct-state tests with failing encapsulation tests**

Replace `tests/domain/test_ru.py` with:

```python
import pytest

from simulator.domain.errors import DomainValidationError
from simulator.domain.ru import RU, RUStatus


def make_ru(**overrides: object) -> RU:
    values = {
        "id": 1,
        "battery": 10.0,
        "status": RUStatus.ACTIVE,
        "active_consumption": 2.0,
        "sleep_consumption": 0.5,
    }
    values.update(overrides)
    return RU(**values)


def test_status_has_sleep_and_active_states() -> None:
    assert {status.value for status in RUStatus} == {"sleep", "active"}


def test_exposes_battery_and_fixed_initial_capacity() -> None:
    ru = make_ru(battery=12.0)

    assert ru.get_battery() == 12.0
    assert ru.get_initial_capacity() == 12.0
    assert not hasattr(ru, "battery")


def test_sets_and_gets_status() -> None:
    ru = make_ru(status=RUStatus.ACTIVE)

    result = ru.set_status(RUStatus.SLEEP)

    assert result is None
    assert ru.get_status() is RUStatus.SLEEP
    assert not hasattr(ru, "status")


def test_rejects_invalid_status_update() -> None:
    ru = make_ru()

    with pytest.raises(DomainValidationError, match="status"):
        ru.set_status("sleep")  # type: ignore[arg-type]


def test_active_ru_uses_default_timestep() -> None:
    ru = make_ru()

    result = ru.update_battery()

    assert result is None
    assert ru.get_battery() == pytest.approx(8.0)
    assert ru.get_initial_capacity() == 10.0


def test_sleeping_ru_uses_custom_timestep() -> None:
    ru = make_ru(status=RUStatus.SLEEP)

    ru.update_battery(delta_time=4.0)

    assert ru.get_battery() == pytest.approx(8.0)


def test_battery_is_clamped_at_zero() -> None:
    ru = make_ru(battery=1.0)

    ru.update_battery()

    assert ru.get_battery() == 0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", 0),
        ("battery", 0.0),
        ("active_consumption", 0.0),
        ("sleep_consumption", 0.0),
        ("id", -1),
        ("battery", -1.0),
        ("active_consumption", -1.0),
        ("sleep_consumption", -1.0),
    ],
)
def test_rejects_non_positive_constructor_values(field: str, value: float) -> None:
    with pytest.raises(DomainValidationError, match=field):
        make_ru(**{field: value})


def test_rejects_invalid_constructor_status() -> None:
    with pytest.raises(DomainValidationError, match="status"):
        make_ru(status="active")
```

- [ ] **Step 2: Run the RU tests and verify the new API is absent**

Run:

```bash
uv run pytest tests/domain/test_ru.py -v
```

Expected: failures report missing `get_battery`, `get_initial_capacity`,
`get_status`, and `set_status`; existing battery tests using the new accessors
also fail.

- [ ] **Step 3: Implement the private RU state and access methods**

Replace `src/simulator/domain/ru.py` with:

```python
from enum import Enum

from simulator.domain.errors import DomainValidationError


class RUStatus(Enum):
    SLEEP = "sleep"
    ACTIVE = "active"


class RU:
    def __init__(
        self,
        id: int,
        battery: float,
        status: RUStatus,
        active_consumption: float,
        sleep_consumption: float,
    ) -> None:
        positive_fields = {
            "id": id,
            "battery": battery,
            "active_consumption": active_consumption,
            "sleep_consumption": sleep_consumption,
        }
        for field, value in positive_fields.items():
            if value <= 0:
                raise DomainValidationError(f"{field} must be positive")
        if not isinstance(status, RUStatus):
            raise DomainValidationError("status must be an RUStatus")

        self.id = id
        self.active_consumption = active_consumption
        self.sleep_consumption = sleep_consumption
        self._battery = battery
        self._initial_capacity = battery
        self._status = status

    def get_battery(self) -> float:
        return self._battery

    def get_initial_capacity(self) -> float:
        return self._initial_capacity

    def get_status(self) -> RUStatus:
        return self._status

    def set_status(self, status: RUStatus) -> None:
        if not isinstance(status, RUStatus):
            raise DomainValidationError("status must be an RUStatus")
        self._status = status

    def update_battery(self, delta_time: float = 1.0) -> None:
        consumption = (
            self.active_consumption
            if self._status is RUStatus.ACTIVE
            else self.sleep_consumption
        )
        self._battery = max(0.0, self._battery - delta_time * consumption)
```

- [ ] **Step 4: Run focused tests and verify they pass**

Run:

```bash
uv run pytest tests/domain/test_ru.py -v
```

Expected: all tests in `tests/domain/test_ru.py` pass.

- [ ] **Step 5: Run all domain tests for compatibility**

Run:

```bash
uv run pytest tests/domain -v
```

Expected: all domain tests pass.

- [ ] **Step 6: Commit the RU encapsulation**

```bash
git add src/simulator/domain/ru.py tests/domain/test_ru.py
git commit -m "refactor: encapsulate RU state"
```

---

### Task 2: Add the Controller Interface and Always-Active Policy

**Files:**
- Create: `tests/controllers/test_always_active.py`
- Modify: `src/simulator/controllers/base.py`
- Modify: `src/simulator/controllers/always_active.py`

**Interfaces:**
- Consumes: Task 1's `RU` access methods, public `RU.id`, and public `RU.active_consumption`.
- Produces: abstract `RUController.update(rus: list[RU], timestamp: int) -> None`, `_validate_timestamp(timestamp: int) -> None`, `_can_activate(ru: RU) -> bool`, `_is_selected_for_timestamp(ru: RU, timestamp: int) -> bool`, and `AlwaysActiveController.update(...)`.

- [ ] **Step 1: Write failing always-active and interface tests**

Create `tests/controllers/test_always_active.py`:

```python
import logging

import pytest

from simulator.controllers.always_active import AlwaysActiveController
from simulator.controllers.base import RUController
from simulator.domain.ru import RU, RUStatus


def make_ru(
    *,
    id: int = 1,
    battery: float = 10.0,
    status: RUStatus = RUStatus.SLEEP,
    active_consumption: float = 2.0,
) -> RU:
    return RU(
        id=id,
        battery=battery,
        status=status,
        active_consumption=active_consumption,
        sleep_consumption=0.5,
    )


def test_controller_interface_is_abstract() -> None:
    with pytest.raises(TypeError):
        RUController()


def test_activates_ru_with_more_than_required_battery() -> None:
    ru = make_ru(battery=3.0)

    AlwaysActiveController().update([ru], timestamp=4)

    assert ru.get_status() is RUStatus.ACTIVE


def test_activates_ru_with_exactly_required_battery() -> None:
    ru = make_ru(battery=2.0)

    AlwaysActiveController().update([ru], timestamp=4)

    assert ru.get_status() is RUStatus.ACTIVE


def test_sleeps_ru_with_insufficient_battery() -> None:
    ru = make_ru(battery=1.0, status=RUStatus.ACTIVE)

    AlwaysActiveController().update([ru], timestamp=4)

    assert ru.get_status() is RUStatus.SLEEP


def test_underpowered_ru_does_not_log(caplog: pytest.LogCaptureFixture) -> None:
    ru = make_ru(battery=1.0, status=RUStatus.ACTIVE)

    with caplog.at_level(logging.INFO):
        AlwaysActiveController().update([ru], timestamp=4)

    assert caplog.records == []


def test_empty_ru_list_is_a_no_op() -> None:
    result = AlwaysActiveController().update([], timestamp=0)

    assert result is None


@pytest.mark.parametrize("timestamp", [-1, 1.5, True])
def test_rejects_invalid_timestamp(timestamp: object) -> None:
    with pytest.raises(ValueError, match="timestamp"):
        AlwaysActiveController().update([], timestamp)  # type: ignore[arg-type]
```

- [ ] **Step 2: Run the tests and verify controller imports fail**

Run:

```bash
uv run pytest tests/controllers/test_always_active.py -v
```

Expected: collection fails because `RUController` and `AlwaysActiveController`
are not defined.

- [ ] **Step 3: Implement the abstract interface and shared helpers**

Replace `src/simulator/controllers/base.py` with:

```python
from abc import ABC, abstractmethod

from simulator.domain.ru import RU


class RUController(ABC):
    @abstractmethod
    def update(self, rus: list[RU], timestamp: int) -> None:
        """Update RU statuses for the supplied timestamp."""

    @staticmethod
    def _validate_timestamp(timestamp: int) -> None:
        if (
            isinstance(timestamp, bool)
            or not isinstance(timestamp, int)
            or timestamp < 0
        ):
            raise ValueError("timestamp must be a non-negative integer")


def _can_activate(ru: RU) -> bool:
    return ru.get_battery() >= ru.active_consumption


def _is_selected_for_timestamp(ru: RU, timestamp: int) -> bool:
    selected_id_parity = (timestamp // 10) % 2
    return ru.id % 2 == selected_id_parity
```

- [ ] **Step 4: Implement the always-active policy**

Replace `src/simulator/controllers/always_active.py` with:

```python
from simulator.controllers.base import RUController, _can_activate
from simulator.domain.ru import RU, RUStatus


class AlwaysActiveController(RUController):
    def update(self, rus: list[RU], timestamp: int) -> None:
        self._validate_timestamp(timestamp)
        for ru in rus:
            status = RUStatus.ACTIVE if _can_activate(ru) else RUStatus.SLEEP
            ru.set_status(status)
```

- [ ] **Step 5: Run focused tests and verify they pass**

Run:

```bash
uv run pytest tests/controllers/test_always_active.py -v
```

Expected: all always-active tests pass.

- [ ] **Step 6: Run RU and always-active tests together**

Run:

```bash
uv run pytest tests/domain/test_ru.py tests/controllers/test_always_active.py -v
```

Expected: both test modules pass.

- [ ] **Step 7: Commit the controller base and always-active policy**

```bash
git add src/simulator/controllers/base.py src/simulator/controllers/always_active.py tests/controllers/test_always_active.py
git commit -m "feat: add always-active RU controller"
```

---

### Task 3: Implement Timestamp-Staggered Activation and Logs

**Files:**
- Create: `tests/controllers/test_staggered_active.py`
- Modify: `src/simulator/controllers/staggered_active.py`

**Interfaces:**
- Consumes: `RUController._validate_timestamp`, `_can_activate(ru)`, `_is_selected_for_timestamp(ru, timestamp)`, and Task 1's RU access methods.
- Produces: `StaggeredActiveController.update(rus: list[RU], timestamp: int) -> None` and module logger `simulator.controllers.staggered_active`.

- [ ] **Step 1: Write failing staggered-policy tests**

Create `tests/controllers/test_staggered_active.py`:

```python
import logging

import pytest

from simulator.controllers.staggered_active import StaggeredActiveController
from simulator.domain.ru import RU, RUStatus


def make_ru(
    id: int,
    *,
    battery: float = 10.0,
    status: RUStatus = RUStatus.ACTIVE,
    active_consumption: float = 2.0,
) -> RU:
    return RU(
        id=id,
        battery=battery,
        status=status,
        active_consumption=active_consumption,
        sleep_consumption=0.5,
    )


@pytest.mark.parametrize(
    ("timestamp", "active_id", "sleeping_id"),
    [
        (9, 2, 1),
        (10, 1, 2),
        (19, 1, 2),
        (20, 2, 1),
    ],
)
def test_selects_group_at_timestamp_boundaries(
    timestamp: int, active_id: int, sleeping_id: int
) -> None:
    rus = [make_ru(1), make_ru(2)]

    StaggeredActiveController().update(rus, timestamp)

    statuses = {ru.id: ru.get_status() for ru in rus}
    assert statuses[active_id] is RUStatus.ACTIVE
    assert statuses[sleeping_id] is RUStatus.SLEEP


def test_selected_ru_with_exact_battery_is_active() -> None:
    ru = make_ru(2, battery=2.0, status=RUStatus.SLEEP)

    StaggeredActiveController().update([ru], timestamp=0)

    assert ru.get_status() is RUStatus.ACTIVE


def test_selected_underpowered_ru_sleeps_and_logs_info(
    caplog: pytest.LogCaptureFixture,
) -> None:
    ru = make_ru(2, battery=1.0)

    with caplog.at_level(
        logging.INFO, logger="simulator.controllers.staggered_active"
    ):
        StaggeredActiveController().update([ru], timestamp=7)

    assert ru.get_status() is RUStatus.SLEEP
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.levelno == logging.INFO
    assert "StaggeredActiveController" in record.getMessage()
    assert "RU 2" in record.getMessage()
    assert "timestamp 7" in record.getMessage()
    assert "battery=1.0" in record.getMessage()
    assert "required=2.0" in record.getMessage()


def test_non_selected_ru_sleeps_without_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    ru = make_ru(1, battery=1.0)

    with caplog.at_level(
        logging.INFO, logger="simulator.controllers.staggered_active"
    ):
        StaggeredActiveController().update([ru], timestamp=0)

    assert ru.get_status() is RUStatus.SLEEP
    assert caplog.records == []


def test_empty_ru_list_is_a_no_op() -> None:
    result = StaggeredActiveController().update([], timestamp=0)

    assert result is None


def test_rejects_invalid_timestamp() -> None:
    with pytest.raises(ValueError, match="timestamp"):
        StaggeredActiveController().update([], timestamp=-1)
```

- [ ] **Step 2: Run the staggered tests and verify the class is absent**

Run:

```bash
uv run pytest tests/controllers/test_staggered_active.py -v
```

Expected: collection fails because `StaggeredActiveController` is not defined.

- [ ] **Step 3: Implement staggered selection and informational logging**

Replace `src/simulator/controllers/staggered_active.py` with:

```python
import logging

from simulator.controllers.base import (
    RUController,
    _can_activate,
    _is_selected_for_timestamp,
)
from simulator.domain.ru import RU, RUStatus

logger = logging.getLogger(__name__)


class StaggeredActiveController(RUController):
    def update(self, rus: list[RU], timestamp: int) -> None:
        self._validate_timestamp(timestamp)
        for ru in rus:
            if not _is_selected_for_timestamp(ru, timestamp):
                ru.set_status(RUStatus.SLEEP)
                continue

            if _can_activate(ru):
                ru.set_status(RUStatus.ACTIVE)
                continue

            ru.set_status(RUStatus.SLEEP)
            logger.info(
                "%s could not activate RU %s at timestamp %s: battery=%s, required=%s",
                type(self).__name__,
                ru.id,
                timestamp,
                ru.get_battery(),
                ru.active_consumption,
            )
```

- [ ] **Step 4: Run focused tests and verify they pass**

Run:

```bash
uv run pytest tests/controllers/test_staggered_active.py -v
```

Expected: all staggered-policy tests pass.

- [ ] **Step 5: Run all implemented controller tests**

Run:

```bash
uv run pytest tests/controllers/test_always_active.py tests/controllers/test_staggered_active.py -v
```

Expected: all always-active and staggered tests pass.

- [ ] **Step 6: Commit the staggered policy**

```bash
git add src/simulator/controllers/staggered_active.py tests/controllers/test_staggered_active.py
git commit -m "feat: add staggered RU controller"
```

---

### Task 4: Implement the Permanent Threshold Transition

**Files:**
- Create: `tests/controllers/test_threshold_staggered_active.py`
- Modify: `src/simulator/controllers/threshold_staggered_active.py`

**Interfaces:**
- Consumes: `RUController._validate_timestamp`, `_can_activate(ru)`, `_is_selected_for_timestamp(ru, timestamp)`, and `RU.get_initial_capacity()`.
- Produces: `ThresholdStaggeredActiveController(threshold_percentage: float)` and `update(rus: list[RU], timestamp: int) -> None` with permanent private `_staggered_started` state.

- [ ] **Step 1: Write failing threshold-policy tests**

Create `tests/controllers/test_threshold_staggered_active.py`:

```python
import logging

import pytest

from simulator.controllers.threshold_staggered_active import (
    ThresholdStaggeredActiveController,
)
from simulator.domain.ru import RU, RUStatus


def make_ru(
    id: int,
    *,
    battery: float = 10.0,
    status: RUStatus = RUStatus.SLEEP,
    active_consumption: float = 1.0,
) -> RU:
    return RU(
        id=id,
        battery=battery,
        status=status,
        active_consumption=active_consumption,
        sleep_consumption=0.5,
    )


def drain_to(ru: RU, target_battery: float) -> None:
    ru.set_status(RUStatus.ACTIVE)
    delta_time = (ru.get_battery() - target_battery) / ru.active_consumption
    ru.update_battery(delta_time=delta_time)


@pytest.mark.parametrize("threshold", [-0.1, 100.1, "50", True])
def test_rejects_invalid_threshold(threshold: object) -> None:
    with pytest.raises(ValueError, match="threshold_percentage"):
        ThresholdStaggeredActiveController(threshold)  # type: ignore[arg-type]


def test_keeps_every_ru_active_before_all_reach_threshold() -> None:
    odd_ru = make_ru(1)
    even_ru = make_ru(2)
    drain_to(odd_ru, 5.0)
    drain_to(even_ru, 6.0)

    controller = ThresholdStaggeredActiveController(50.0)

    controller.update([odd_ru, even_ru], timestamp=0)

    assert odd_ru.get_status() is RUStatus.ACTIVE
    assert even_ru.get_status() is RUStatus.ACTIVE


def test_threshold_equality_for_every_ru_starts_staggering() -> None:
    odd_ru = make_ru(1)
    even_ru = make_ru(2)
    drain_to(odd_ru, 5.0)
    drain_to(even_ru, 5.0)

    controller = ThresholdStaggeredActiveController(50.0)

    controller.update([odd_ru, even_ru], timestamp=0)

    assert odd_ru.get_status() is RUStatus.SLEEP
    assert even_ru.get_status() is RUStatus.ACTIVE


def test_transition_uses_global_timestamp_without_restart() -> None:
    odd_ru = make_ru(1)
    even_ru = make_ru(2)
    drain_to(odd_ru, 5.0)
    drain_to(even_ru, 5.0)

    controller = ThresholdStaggeredActiveController(50.0)

    controller.update([odd_ru, even_ru], timestamp=37)

    assert odd_ru.get_status() is RUStatus.ACTIVE
    assert even_ru.get_status() is RUStatus.SLEEP


def test_transition_remains_permanent_for_later_ru_collection() -> None:
    controller = ThresholdStaggeredActiveController(50.0)
    first_odd = make_ru(1)
    first_even = make_ru(2)
    drain_to(first_odd, 5.0)
    drain_to(first_even, 5.0)
    controller.update([first_odd, first_even], timestamp=0)
    replacement_odd = make_ru(1)
    replacement_even = make_ru(2)

    controller.update([replacement_odd, replacement_even], timestamp=10)

    assert replacement_odd.get_status() is RUStatus.ACTIVE
    assert replacement_even.get_status() is RUStatus.SLEEP


def test_empty_list_does_not_start_transition() -> None:
    controller = ThresholdStaggeredActiveController(50.0)
    controller.update([], timestamp=0)
    odd_ru = make_ru(1)
    even_ru = make_ru(2)

    controller.update([odd_ru, even_ru], timestamp=10)

    assert odd_ru.get_status() is RUStatus.ACTIVE
    assert even_ru.get_status() is RUStatus.ACTIVE


def test_underpowered_ru_logs_info_before_transition(
    caplog: pytest.LogCaptureFixture,
) -> None:
    ru = make_ru(1, battery=1.0, active_consumption=2.0)

    with caplog.at_level(
        logging.INFO,
        logger="simulator.controllers.threshold_staggered_active",
    ):
        ThresholdStaggeredActiveController(0.0).update([ru], timestamp=3)

    assert ru.get_status() is RUStatus.SLEEP
    assert len(caplog.records) == 1
    message = caplog.records[0].getMessage()
    assert caplog.records[0].levelno == logging.INFO
    assert "ThresholdStaggeredActiveController" in message
    assert "RU 1" in message
    assert "timestamp 3" in message
    assert "battery=1.0" in message
    assert "required=2.0" in message


def test_selected_underpowered_ru_logs_info_after_transition(
    caplog: pytest.LogCaptureFixture,
) -> None:
    ru = make_ru(2, battery=1.0, active_consumption=2.0)

    with caplog.at_level(
        logging.INFO,
        logger="simulator.controllers.threshold_staggered_active",
    ):
        ThresholdStaggeredActiveController(100.0).update([ru], timestamp=0)

    assert ru.get_status() is RUStatus.SLEEP
    assert len(caplog.records) == 1


def test_rejects_invalid_timestamp() -> None:
    with pytest.raises(ValueError, match="timestamp"):
        ThresholdStaggeredActiveController(50.0).update([], timestamp=-1)
```

- [ ] **Step 2: Run the threshold tests and verify the class is absent**

Run:

```bash
uv run pytest tests/controllers/test_threshold_staggered_active.py -v
```

Expected: collection fails because `ThresholdStaggeredActiveController` is not
defined.

- [ ] **Step 3: Implement threshold validation and one-way mode transition**

Replace `src/simulator/controllers/threshold_staggered_active.py` with:

```python
import logging

from simulator.controllers.base import (
    RUController,
    _can_activate,
    _is_selected_for_timestamp,
)
from simulator.domain.ru import RU, RUStatus

logger = logging.getLogger(__name__)


class ThresholdStaggeredActiveController(RUController):
    def __init__(self, threshold_percentage: float) -> None:
        if (
            isinstance(threshold_percentage, bool)
            or not isinstance(threshold_percentage, int | float)
            or not 0 <= threshold_percentage <= 100
        ):
            raise ValueError("threshold_percentage must be between 0 and 100")
        self.threshold_percentage = float(threshold_percentage)
        self._staggered_started = False

    def update(self, rus: list[RU], timestamp: int) -> None:
        self._validate_timestamp(timestamp)
        if not rus:
            return

        if not self._staggered_started and all(
            ru.get_battery() / ru.get_initial_capacity() * 100
            <= self.threshold_percentage
            for ru in rus
        ):
            self._staggered_started = True

        for ru in rus:
            selected = not self._staggered_started or _is_selected_for_timestamp(
                ru, timestamp
            )
            if not selected:
                ru.set_status(RUStatus.SLEEP)
                continue

            if _can_activate(ru):
                ru.set_status(RUStatus.ACTIVE)
                continue

            ru.set_status(RUStatus.SLEEP)
            logger.info(
                "%s could not activate RU %s at timestamp %s: battery=%s, required=%s",
                type(self).__name__,
                ru.id,
                timestamp,
                ru.get_battery(),
                ru.active_consumption,
            )
```

- [ ] **Step 4: Run focused tests and verify they pass**

Run:

```bash
uv run pytest tests/controllers/test_threshold_staggered_active.py -v
```

Expected: all threshold-staggered tests pass.

- [ ] **Step 5: Run all controller tests**

Run:

```bash
uv run pytest tests/controllers -v
```

Expected: all controller tests pass.

- [ ] **Step 6: Commit the threshold policy**

```bash
git add src/simulator/controllers/threshold_staggered_active.py tests/controllers/test_threshold_staggered_active.py
git commit -m "feat: add threshold-staggered RU controller"
```

---

### Task 5: Expose the Controller API and Document the Feature

**Files:**
- Create: `tests/controllers/test_public_imports.py`
- Modify: `src/simulator/controllers/__init__.py`
- Modify: `README.md`

**Interfaces:**
- Consumes: `RUController`, `AlwaysActiveController`, `StaggeredActiveController`, and `ThresholdStaggeredActiveController` from Tasks 2–4.
- Produces: supported imports for all four classes from `simulator.controllers` and README guidance matching the implemented behavior.

- [ ] **Step 1: Write a failing public-import test**

Create `tests/controllers/test_public_imports.py`:

```python
from simulator.controllers import (
    AlwaysActiveController,
    RUController,
    StaggeredActiveController,
    ThresholdStaggeredActiveController,
)


def test_controller_classes_are_publicly_importable() -> None:
    assert AlwaysActiveController.__name__ == "AlwaysActiveController"
    assert RUController.__name__ == "RUController"
    assert StaggeredActiveController.__name__ == "StaggeredActiveController"
    assert (
        ThresholdStaggeredActiveController.__name__
        == "ThresholdStaggeredActiveController"
    )
```

- [ ] **Step 2: Run the public-import test and verify collection fails**

Run:

```bash
uv run pytest tests/controllers/test_public_imports.py -v
```

Expected: collection fails because the controller package does not export the
classes.

- [ ] **Step 3: Add the controller package exports**

Replace `src/simulator/controllers/__init__.py` with:

```python
from simulator.controllers.always_active import AlwaysActiveController
from simulator.controllers.base import RUController
from simulator.controllers.staggered_active import StaggeredActiveController
from simulator.controllers.threshold_staggered_active import (
    ThresholdStaggeredActiveController,
)

__all__ = [
    "AlwaysActiveController",
    "RUController",
    "StaggeredActiveController",
    "ThresholdStaggeredActiveController",
]
```

- [ ] **Step 4: Run the public-import and controller test suites**

Run:

```bash
uv run pytest tests/controllers -v
```

Expected: all controller tests pass, including the public-import test.

- [ ] **Step 5: Update README feature documentation**

Replace the introductory status paragraph in `README.md`:

```markdown
The repository currently implements the core `Point`, `User`, and `RU` domain
models plus always-active, timestamp-staggered, and battery-threshold-staggered
RU control policies. Simulation orchestration and metric calculations remain
scaffolded for later phases.
```

Add this section after `## Domain Models` and before `## Setup`:

```markdown
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
```

- [ ] **Step 6: Run the full verification set**

Run each command separately:

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

Expected: pytest reports all tests passed; Ruff lint reports `All checks
passed!`; Ruff formatting reports that all files are already formatted.

If the formatting check identifies files, run `uv run ruff format .`, inspect
the formatting-only diff, and repeat all three verification commands.

- [ ] **Step 7: Inspect the final diff for scope and generated files**

Run:

```bash
git status --short
git diff --check
git diff -- src tests README.md
```

Expected: only the planned RU, controller, test, and README files are modified;
`git diff --check` produces no output; no environment, cache, lockfile, or
unrelated files appear.

- [ ] **Step 8: Commit the exports and documentation**

```bash
git add src/simulator/controllers/__init__.py tests/controllers/test_public_imports.py README.md
git commit -m "docs: expose RU controller policies"
```

- [ ] **Step 9: Confirm the repository is clean and the final commits exist**

Run:

```bash
git status --short
git log -5 --oneline
```

Expected: `git status --short` produces no output and the recent history shows
the five focused implementation commits after the approved design and plan
commits.
