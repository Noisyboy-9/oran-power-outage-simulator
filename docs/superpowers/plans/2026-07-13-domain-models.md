# Domain Models Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement validated `Point`, `User`, and `RU` domain objects, including status-based RU battery depletion.

**Architecture:** Use focused standard-library dataclasses in the existing domain modules. Put the shared validation exception in its own module, keep `Point` and `User` immutable, keep `RU` mutable, and expose the approved public types through `simulator.domain`.

**Tech Stack:** Python 3.12, standard library (`dataclasses`, `enum`, `math`), pytest, Ruff

## Global Constraints

- IDs are `int` values and must be strictly positive.
- Point coordinates are `float` values and must be non-negative.
- Initial RU battery and both consumption rates must be strictly positive.
- Invalid constructor values raise `DomainValidationError`.
- `RU.update_battery(delta_time: float = 1.0) -> None` mutates battery and clamps it at zero.
- Do not add timestep validation or unrelated simulation behavior.

---

### Task 1: Domain exception and Point

**Files:**

- Create: `src/simulator/domain/errors.py`
- Modify: `src/simulator/domain/point.py`
- Create: `tests/domain/test_point.py`

**Interfaces:**

- Consumes: Python numeric coordinates.
- Produces: `DomainValidationError(ValueError)` and immutable `Point(x: float, y: float)` with `distance_to(other: Point) -> float`.

- [ ] **Step 1: Write the failing Point tests**

```python
import pytest

from simulator.domain.errors import DomainValidationError
from simulator.domain.point import Point


def test_calculates_cartesian_distance() -> None:
    assert Point(0, 0).distance_to(Point(3, 4)) == pytest.approx(5)


def test_distance_to_same_point_is_zero() -> None:
    point = Point(2, 3)
    assert point.distance_to(point) == 0


@pytest.mark.parametrize(("x", "y"), [(-1, 0), (0, -1)])
def test_rejects_negative_coordinates(x: float, y: float) -> None:
    with pytest.raises(DomainValidationError):
        Point(x, y)
```

- [ ] **Step 2: Run the Point tests and verify RED**

Run: `uv run pytest tests/domain/test_point.py -v`

Expected: collection fails because `DomainValidationError` and `Point` do not exist yet.

- [ ] **Step 3: Add the minimal exception and Point implementation**

```python
# src/simulator/domain/errors.py
class DomainValidationError(ValueError):
    """Raised when a domain object receives an invalid value."""
```

```python
# src/simulator/domain/point.py
from __future__ import annotations

from dataclasses import dataclass
from math import hypot

from simulator.domain.errors import DomainValidationError


@dataclass(frozen=True)
class Point:
    x: float
    y: float

    def __post_init__(self) -> None:
        if self.x < 0:
            raise DomainValidationError("x must be non-negative")
        if self.y < 0:
            raise DomainValidationError("y must be non-negative")

    def distance_to(self, other: Point) -> float:
        return hypot(self.x - other.x, self.y - other.y)
```

- [ ] **Step 4: Run the Point tests and verify GREEN**

Run: `uv run pytest tests/domain/test_point.py -v`

Expected: 4 tests pass.

- [ ] **Step 5: Commit the Point slice**

```bash
git add src/simulator/domain/errors.py src/simulator/domain/point.py tests/domain/test_point.py
git commit -m "feat: add validated point domain model"
```

### Task 2: User

**Files:**

- Modify: `src/simulator/domain/user.py`
- Create: `tests/domain/test_user.py`

**Interfaces:**

- Consumes: `DomainValidationError` from Task 1.
- Produces: immutable `User(id: int)`.

- [ ] **Step 1: Write the failing User tests**

```python
import pytest

from simulator.domain.errors import DomainValidationError
from simulator.domain.user import User


def test_stores_integer_id() -> None:
    assert User(id=1).id == 1


def test_users_with_same_id_are_equal() -> None:
    assert User(id=1) == User(id=1)


@pytest.mark.parametrize("user_id", [0, -1])
def test_rejects_non_positive_id(user_id: int) -> None:
    with pytest.raises(DomainValidationError):
        User(id=user_id)
```

- [ ] **Step 2: Run the User tests and verify RED**

Run: `uv run pytest tests/domain/test_user.py -v`

Expected: collection fails because `User` does not exist yet.

- [ ] **Step 3: Add the minimal User implementation**

```python
from dataclasses import dataclass

from simulator.domain.errors import DomainValidationError


@dataclass(frozen=True)
class User:
    id: int

    def __post_init__(self) -> None:
        if self.id <= 0:
            raise DomainValidationError("id must be positive")
```

- [ ] **Step 4: Run the User tests and verify GREEN**

Run: `uv run pytest tests/domain/test_user.py -v`

Expected: 4 tests pass.

- [ ] **Step 5: Commit the User slice**

```bash
git add src/simulator/domain/user.py tests/domain/test_user.py
git commit -m "feat: add validated user domain model"
```

### Task 3: Radio Unit

**Files:**

- Modify: `src/simulator/domain/ru.py`
- Create: `tests/domain/test_ru.py`

**Interfaces:**

- Consumes: `DomainValidationError` from Task 1.
- Produces: `RUStatus` with `SLEEP` and `ACTIVE`; mutable `RU`; `RU.update_battery(delta_time: float = 1.0) -> None`.

- [ ] **Step 1: Write the failing RU tests**

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


def test_active_ru_uses_default_timestep() -> None:
    ru = make_ru()
    result = ru.update_battery()
    assert result is None
    assert ru.battery == pytest.approx(8.0)


def test_sleeping_ru_uses_custom_timestep() -> None:
    ru = make_ru(status=RUStatus.SLEEP)
    ru.update_battery(delta_time=4.0)
    assert ru.battery == pytest.approx(8.0)


def test_battery_is_clamped_at_zero() -> None:
    ru = make_ru(battery=1.0)
    ru.update_battery()
    assert ru.battery == 0


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
```

- [ ] **Step 2: Run the RU tests and verify RED**

Run: `uv run pytest tests/domain/test_ru.py -v`

Expected: collection fails because `RU` and `RUStatus` do not exist yet.

- [ ] **Step 3: Add the minimal RU implementation**

```python
from dataclasses import dataclass
from enum import Enum

from simulator.domain.errors import DomainValidationError


class RUStatus(Enum):
    SLEEP = "sleep"
    ACTIVE = "active"


@dataclass
class RU:
    id: int
    battery: float
    status: RUStatus
    active_consumption: float
    sleep_consumption: float

    def __post_init__(self) -> None:
        positive_fields = {
            "id": self.id,
            "battery": self.battery,
            "active_consumption": self.active_consumption,
            "sleep_consumption": self.sleep_consumption,
        }
        for field, value in positive_fields.items():
            if value <= 0:
                raise DomainValidationError(f"{field} must be positive")

    def update_battery(self, delta_time: float = 1.0) -> None:
        consumption = (
            self.active_consumption
            if self.status is RUStatus.ACTIVE
            else self.sleep_consumption
        )
        self.battery = max(0.0, self.battery - delta_time * consumption)
```

- [ ] **Step 4: Run the RU tests and verify GREEN**

Run: `uv run pytest tests/domain/test_ru.py -v`

Expected: 12 tests pass.

- [ ] **Step 5: Commit the RU slice**

```bash
git add src/simulator/domain/ru.py tests/domain/test_ru.py
git commit -m "feat: add radio unit battery model"
```

### Task 4: Public domain API and full verification

**Files:**

- Modify: `src/simulator/domain/__init__.py`
- Create: `tests/domain/test_domain.py`

**Interfaces:**

- Consumes: all domain types produced by Tasks 1-3.
- Produces: public imports `Point`, `User`, `RU`, `RUStatus`, and `DomainValidationError` from `simulator.domain`.

- [ ] **Step 1: Write the failing public API test**

```python
from simulator.domain import DomainValidationError, Point, RU, RUStatus, User


def test_domain_types_are_publicly_importable() -> None:
    assert Point.__name__ == "Point"
    assert User.__name__ == "User"
    assert RU.__name__ == "RU"
    assert RUStatus.__name__ == "RUStatus"
    assert issubclass(DomainValidationError, ValueError)
```

- [ ] **Step 2: Run the public API test and verify RED**

Run: `uv run pytest tests/domain/test_domain.py -v`

Expected: collection fails because the domain package does not export these names.

- [ ] **Step 3: Add the public exports**

```python
from simulator.domain.errors import DomainValidationError
from simulator.domain.point import Point
from simulator.domain.ru import RU, RUStatus
from simulator.domain.user import User

__all__ = ["DomainValidationError", "Point", "RU", "RUStatus", "User"]
```

- [ ] **Step 4: Run focused and full verification**

Run: `uv run pytest tests/domain -v`

Expected: all domain tests pass.

Run: `uv run pytest`

Expected: all repository tests pass.

Run: `uv run ruff check .`

Expected: `All checks passed!`

Run: `uv run ruff format --check .`

Expected: all files are already formatted.

- [ ] **Step 5: Commit the public API and plan**

```bash
git add src/simulator/domain/__init__.py tests/domain/test_domain.py docs/superpowers/plans/2026-07-13-domain-models.md
git commit -m "feat: expose domain models"
```
