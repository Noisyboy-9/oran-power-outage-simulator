# Environment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fully initialized static environment with an occupied cell map, uniform RUs, users, collision-free seeded placement, and a distance-limited weighted NetworkX graph.

**Architecture:** Replace `Point` with one immutable `MapCell` domain type, then add a focused `simulator.environment` package containing nested immutable configuration, environment errors, and the state-owning `Environment`. `Environment(config)` constructs all state immediately, protects its structural collections through copies, and uses one seeded random generator for placement and edge weights.

**Tech Stack:** Python 3.12, standard-library dataclasses/random/math, NetworkX, pytest, Ruff, uv, Git

## Global Constraints

- Work only on the `feat/environment` feature branch in the isolated worktree.
- Remove `Point` completely; do not retain a compatibility alias or module.
- Use `MapCell` as the only location type and keep it immutable.
- Store the map in row-major order as `map[y][x]`.
- Require at least one RU and at least one user, and reject entity totals larger than the map area.
- Construct all RUs from one uniform `RUConfig`.
- Treat `distance >= coverage_radius` as disconnected.
- Calculate connected weights as `(1 - random()) * (1 - distance / coverage_radius)`.
- Use one `random.Random(random_seed)` instance for placement and weights.
- For Tasks 1 through 3, start with an executed discovery test that fails inside
  the test body; a pytest collection error does not satisfy the RED phase.
- Do not add mobility, runtime entity changes, reset, graph recalculation, or heterogeneous RU settings.
- Use `uv add` for the NetworkX dependency and commit the updated `uv.lock`.
- Preserve Python `>=3.12` and unrelated user changes.
- Run pytest, Ruff lint, Ruff format check, and `git diff --check` before completion.

---

## File Map

- Delete `src/simulator/domain/point.py`: remove the obsolete location model.
- Delete `tests/domain/test_point.py`: remove obsolete `Point` coverage.
- Create `src/simulator/domain/map_cell.py`: immutable coordinates, occupancy, validation, and distance.
- Create `tests/domain/test_map_cell.py`: externally visible `MapCell` behavior.
- Modify `src/simulator/domain/__init__.py`: export `MapCell` and remove `Point`.
- Modify `tests/domain/test_domain.py`: verify the revised public domain API.
- Delete `src/simulator/environment.py`: replace the empty module with a package.
- Create `src/simulator/environment/__init__.py`: public environment API.
- Create `src/simulator/environment/errors.py`: `EnvironmentValidationError`.
- Create `src/simulator/environment/config.py`: `MapConfig`, `RUConfig`, and `EnvironmentConfig`.
- Create `tests/environment/test_config.py`: nested configuration and validation coverage.
- Create `tests/environment/test_public_imports.py`: supported environment imports.
- Create `src/simulator/environment/environment.py`: environment construction, placement, getters, graph creation, and weight lookup.
- Delete `tests/test_environment.py`: replace the empty root placeholder with focused tests.
- Create `tests/environment/test_environment.py`: construction, placement, consistency, and copy behavior.
- Create `tests/environment/test_connectivity.py`: NetworkX topology, weighting, reproducibility, and lookup behavior.
- Modify `pyproject.toml`: add NetworkX as a runtime dependency through uv.
- Modify `uv.lock`: lock NetworkX through uv.
- Modify `README.md`: document the implemented domain and environment API.
- Modify `AGENTS.md`: replace the obsolete `Point` repository-layout reference.

---

### Task 1: Replace Point with Immutable MapCell

**Files:**

- Delete: `src/simulator/domain/point.py`
- Delete: `tests/domain/test_point.py`
- Create: `src/simulator/domain/map_cell.py`
- Create: `tests/domain/test_map_cell.py`
- Modify: `src/simulator/domain/__init__.py`
- Modify: `tests/domain/test_domain.py`

**Interfaces:**

- Consumes: `DomainValidationError`, `RU`, and `User`.
- Produces: `MapCell(x: int, y: int, occupant: RU | User | None = None)` and `MapCell.distance_to(other: MapCell) -> float`.

- [ ] **Step 1: Establish an executed RED test, then build the final MapCell tests incrementally**

First replace `tests/domain/test_point.py` with this temporary discovery test:

```python
from importlib import import_module


def test_map_cell_module_exists() -> None:
    import_module("simulator.domain.map_cell")
```

Run this test before creating the module. After observing the expected failure
inside the test body, use repeated red/green cycles to replace the temporary
test with the final files below. Add each behavior test before its corresponding
implementation; do not use a collection error as RED evidence.

Rename the temporary test file to `tests/domain/test_map_cell.py` and finish it
with:

```python
from dataclasses import FrozenInstanceError

import pytest

from simulator.domain.errors import DomainValidationError
from simulator.domain.map_cell import MapCell
from simulator.domain.ru import RU, RUStatus
from simulator.domain.user import User


def make_ru() -> RU:
    return RU(
        id=1,
        battery=10.0,
        status=RUStatus.ACTIVE,
        active_consumption=2.0,
        sleep_consumption=0.5,
    )


def test_stores_coordinates_and_empty_occupancy() -> None:
    cell = MapCell(x=2, y=3)

    assert (cell.x, cell.y) == (2, 3)
    assert cell.occupant is None


@pytest.mark.parametrize("occupant", [make_ru(), User(id=1)])
def test_stores_supported_occupant(occupant: RU | User) -> None:
    assert MapCell(x=0, y=0, occupant=occupant).occupant is occupant


def test_calculates_cartesian_distance() -> None:
    assert MapCell(0, 0).distance_to(MapCell(3, 4)) == pytest.approx(5)


def test_distance_to_same_cell_is_zero() -> None:
    cell = MapCell(2, 3)

    assert cell.distance_to(cell) == 0


@pytest.mark.parametrize(
    ("x", "y"),
    [
        (-1, 0),
        (0, -1),
        (1.5, 0),
        (0, 1.5),
        (True, 0),
        (0, False),
    ],
)
def test_rejects_invalid_coordinates(x: object, y: object) -> None:
    with pytest.raises(DomainValidationError, match="coordinate"):
        MapCell(x=x, y=y)  # type: ignore[arg-type]


def test_rejects_invalid_occupant() -> None:
    with pytest.raises(DomainValidationError, match="occupant"):
        MapCell(x=0, y=0, occupant=object())  # type: ignore[arg-type]


def test_is_immutable() -> None:
    cell = MapCell(x=0, y=0)

    with pytest.raises(FrozenInstanceError):
        cell.occupant = User(id=1)  # type: ignore[misc]
```

Replace `tests/domain/test_domain.py` with:

```python
import simulator.domain as domain
from simulator.domain import DomainValidationError, MapCell, RU, RUStatus, User


def test_domain_types_are_publicly_importable() -> None:
    assert MapCell.__name__ == "MapCell"
    assert User.__name__ == "User"
    assert RU.__name__ == "RU"
    assert RUStatus.__name__ == "RUStatus"
    assert issubclass(DomainValidationError, ValueError)
    assert not hasattr(domain, "Point")
```

- [ ] **Step 2: Run the focused domain tests to verify they fail**

Run the temporary discovery test before creating the module:

```bash
uv run pytest tests/domain/test_point.py::test_map_cell_module_exists -v
```

Expected: pytest executes the test and marks it failed with
`ModuleNotFoundError: No module named 'simulator.domain.map_cell'`.

- [ ] **Step 3: Implement MapCell and remove Point**

Delete `src/simulator/domain/point.py`. Create `src/simulator/domain/map_cell.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass
from math import hypot

from simulator.domain.errors import DomainValidationError
from simulator.domain.ru import RU
from simulator.domain.user import User


@dataclass(frozen=True)
class MapCell:
    x: int
    y: int
    occupant: RU | User | None = None

    def __post_init__(self) -> None:
        coordinates = {"x": self.x, "y": self.y}
        for name, value in coordinates.items():
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise DomainValidationError(
                    f"{name} coordinate must be a non-negative integer"
                )

        if self.occupant is not None and not isinstance(
            self.occupant, (RU, User)
        ):
            raise DomainValidationError("occupant must be an RU, User, or None")

    def distance_to(self, other: MapCell) -> float:
        return hypot(self.x - other.x, self.y - other.y)
```

Replace `src/simulator/domain/__init__.py` with:

```python
from simulator.domain.errors import DomainValidationError
from simulator.domain.map_cell import MapCell
from simulator.domain.ru import RU, RUStatus
from simulator.domain.user import User

__all__ = ["DomainValidationError", "MapCell", "RU", "RUStatus", "User"]
```

- [ ] **Step 4: Run domain tests and Ruff**

Run:

```bash
uv run pytest tests/domain -v
uv run ruff check src/simulator/domain tests/domain
uv run ruff format --check src/simulator/domain tests/domain
```

Expected: all domain tests pass and Ruff reports no lint or formatting errors.

- [ ] **Step 5: Commit the domain replacement**

Run:

```bash
git add src/simulator/domain tests/domain
git diff --cached --check
git commit -m "refactor: replace Point with MapCell"
```

Expected: the commit contains only the domain replacement and its tests.

---

### Task 2: Add Nested Environment Configuration

**Files:**

- Delete: `src/simulator/environment.py`
- Create: `src/simulator/environment/__init__.py`
- Create: `src/simulator/environment/errors.py`
- Create: `src/simulator/environment/config.py`
- Create: `tests/environment/test_config.py`
- Create: `tests/environment/test_public_imports.py`

**Interfaces:**

- Consumes: `RUStatus`.
- Produces: `EnvironmentValidationError`, `MapConfig`, `RUConfig`, and `EnvironmentConfig`.

- [ ] **Step 1: Establish an executed RED test, then build the final configuration tests incrementally**

First create `tests/environment/test_config.py` with this temporary discovery
test:

```python
from importlib import import_module


def test_environment_config_module_exists() -> None:
    import_module("simulator.environment.config")
```

Run this test before replacing the empty environment module. After observing
the expected failure inside the test body, use repeated red/green cycles to
replace the temporary test with the final configuration tests below. Add each
validation test before its corresponding implementation.

Finish `tests/environment/test_config.py` with:

```python
from dataclasses import FrozenInstanceError

import pytest

from simulator.domain.ru import RUStatus
from simulator.environment import (
    EnvironmentConfig,
    EnvironmentValidationError,
    MapConfig,
    RUConfig,
)


def make_ru_config(**overrides: object) -> RUConfig:
    values = {
        "count": 2,
        "initial_battery": 100.0,
        "initial_status": RUStatus.ACTIVE,
        "active_consumption": 2.0,
        "sleep_consumption": 0.5,
        "coverage_radius": 4.0,
    }
    values.update(overrides)
    return RUConfig(**values)  # type: ignore[arg-type]


def make_environment_config(**overrides: object) -> EnvironmentConfig:
    values = {
        "map": MapConfig(width=3, height=2),
        "ru": make_ru_config(),
        "user_count": 2,
        "random_seed": 7,
    }
    values.update(overrides)
    return EnvironmentConfig(**values)  # type: ignore[arg-type]


def test_stores_nested_configuration() -> None:
    config = make_environment_config()

    assert config.map == MapConfig(width=3, height=2)
    assert config.ru == make_ru_config()
    assert config.user_count == 2
    assert config.random_seed == 7


@pytest.mark.parametrize(
    ("config", "field", "value"),
    [
        (MapConfig(2, 2), "width", 3),
        (make_ru_config(), "count", 3),
        (make_environment_config(), "user_count", 3),
    ],
)
def test_configuration_is_immutable(
    config: object, field: str, value: object
) -> None:
    with pytest.raises(FrozenInstanceError):
        setattr(config, field, value)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("width", 0),
        ("width", -1),
        ("width", 1.5),
        ("width", True),
        ("height", 0),
        ("height", -1),
        ("height", 1.5),
        ("height", False),
    ],
)
def test_rejects_invalid_map_dimensions(field: str, value: object) -> None:
    values = {"width": 2, "height": 2, field: value}

    with pytest.raises(EnvironmentValidationError, match=field):
        MapConfig(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("count", [0, -1, 1.5, True])
def test_rejects_invalid_ru_count(count: object) -> None:
    with pytest.raises(EnvironmentValidationError, match="count"):
        make_ru_config(count=count)


@pytest.mark.parametrize(
    "coverage_radius", [0.0, -1.0, float("nan"), True, "wide"]
)
def test_rejects_invalid_coverage_radius(coverage_radius: object) -> None:
    with pytest.raises(EnvironmentValidationError, match="coverage_radius"):
        make_ru_config(coverage_radius=coverage_radius)


@pytest.mark.parametrize(
    ("field", "value"),
    [("map", object()), ("ru", object())],
)
def test_rejects_invalid_nested_configuration(field: str, value: object) -> None:
    with pytest.raises(EnvironmentValidationError, match=field):
        make_environment_config(**{field: value})


@pytest.mark.parametrize("user_count", [0, -1, 1.5, True])
def test_rejects_invalid_user_count(user_count: object) -> None:
    with pytest.raises(EnvironmentValidationError, match="user_count"):
        make_environment_config(user_count=user_count)


def test_rejects_entity_count_larger_than_map() -> None:
    with pytest.raises(EnvironmentValidationError, match="map capacity"):
        make_environment_config(
            map=MapConfig(width=2, height=2),
            ru=make_ru_config(count=3),
            user_count=2,
        )


def test_accepts_entity_count_equal_to_map_capacity() -> None:
    config = make_environment_config(
        map=MapConfig(width=2, height=2),
        ru=make_ru_config(count=2),
        user_count=2,
    )

    assert config.ru.count + config.user_count == 4


@pytest.mark.parametrize("random_seed", [True, 1.5, "7"])
def test_rejects_invalid_random_seed(random_seed: object) -> None:
    with pytest.raises(EnvironmentValidationError, match="random_seed"):
        make_environment_config(random_seed=random_seed)


@pytest.mark.parametrize("random_seed", [None, 0, -3])
def test_accepts_supported_random_seed(random_seed: int | None) -> None:
    config = make_environment_config(random_seed=random_seed)

    assert config.random_seed == random_seed
```

Create `tests/environment/test_public_imports.py` with:

```python
from simulator.environment import (
    EnvironmentConfig,
    EnvironmentValidationError,
    MapConfig,
    RUConfig,
)


def test_environment_configuration_types_are_publicly_importable() -> None:
    assert MapConfig.__name__ == "MapConfig"
    assert RUConfig.__name__ == "RUConfig"
    assert EnvironmentConfig.__name__ == "EnvironmentConfig"
    assert issubclass(EnvironmentValidationError, ValueError)
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run the temporary discovery test before replacing the module:

```bash
uv run pytest tests/environment/test_config.py::test_environment_config_module_exists -v
```

Expected: pytest executes the test and marks it failed because
`simulator.environment` is not yet a package containing `config`.

- [ ] **Step 3: Replace the module with the environment package and implement configuration**

Delete `src/simulator/environment.py`. Create `src/simulator/environment/errors.py` with:

```python
class EnvironmentValidationError(ValueError):
    """Raised when environment configuration is invalid."""
```

Create `src/simulator/environment/config.py` with:

```python
from dataclasses import dataclass

from simulator.domain.ru import RUStatus
from simulator.environment.errors import EnvironmentValidationError


def _require_positive_integer(name: str, value: object) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise EnvironmentValidationError(f"{name} must be a positive integer")


def _require_positive_number(name: str, value: object) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not value > 0
    ):
        raise EnvironmentValidationError(f"{name} must be positive")


@dataclass(frozen=True)
class MapConfig:
    width: int
    height: int

    def __post_init__(self) -> None:
        _require_positive_integer("width", self.width)
        _require_positive_integer("height", self.height)


@dataclass(frozen=True)
class RUConfig:
    count: int
    initial_battery: float
    initial_status: RUStatus
    active_consumption: float
    sleep_consumption: float
    coverage_radius: float

    def __post_init__(self) -> None:
        _require_positive_integer("count", self.count)
        _require_positive_number("coverage_radius", self.coverage_radius)


@dataclass(frozen=True)
class EnvironmentConfig:
    map: MapConfig
    ru: RUConfig
    user_count: int
    random_seed: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.map, MapConfig):
            raise EnvironmentValidationError("map must be a MapConfig")
        if not isinstance(self.ru, RUConfig):
            raise EnvironmentValidationError("ru must be an RUConfig")

        _require_positive_integer("user_count", self.user_count)

        entity_count = self.ru.count + self.user_count
        if entity_count > self.map.width * self.map.height:
            raise EnvironmentValidationError("entity count exceeds map capacity")

        if self.random_seed is not None and (
            isinstance(self.random_seed, bool)
            or not isinstance(self.random_seed, int)
        ):
            raise EnvironmentValidationError("random_seed must be an integer or None")
```

Create `src/simulator/environment/__init__.py` with:

```python
from simulator.environment.config import EnvironmentConfig, MapConfig, RUConfig
from simulator.environment.errors import EnvironmentValidationError

__all__ = [
    "EnvironmentConfig",
    "EnvironmentValidationError",
    "MapConfig",
    "RUConfig",
]
```

- [ ] **Step 4: Run configuration tests and Ruff**

Run:

```bash
uv run pytest tests/environment/test_config.py tests/environment/test_public_imports.py -v
uv run ruff check src/simulator/environment tests/environment
uv run ruff format --check src/simulator/environment tests/environment
```

Expected: all focused tests pass and Ruff reports no lint or formatting errors.

- [ ] **Step 5: Commit nested environment configuration**

Run:

```bash
git add src/simulator/environment.py src/simulator/environment tests/environment
git diff --cached --check
git commit -m "feat: add environment configuration"
```

Expected: the empty module is replaced by the package, and configuration tests pass.

---

### Task 3: Construct the Map, Entities, and Placements

**Files:**

- Create: `src/simulator/environment/environment.py`
- Modify: `src/simulator/environment/__init__.py`
- Modify: `tests/environment/test_public_imports.py`
- Delete: `tests/test_environment.py`
- Create: `tests/environment/test_environment.py`

**Interfaces:**

- Consumes: `EnvironmentConfig`, `MapCell`, `RU`, `RUStatus`, and `User`.
- Produces: `Environment(config: EnvironmentConfig)`, `get_map()`, `get_rus()`, `get_users()`, `get_ru_locations()`, and `get_user_locations()`.

- [ ] **Step 1: Establish an executed RED test, then build the final construction tests incrementally**

First create `tests/environment/test_environment.py` with this temporary
discovery test:

```python
from importlib import import_module


def test_environment_is_publicly_available() -> None:
    module = import_module("simulator.environment")

    assert hasattr(module, "Environment")
```

Run this test before creating the `Environment` class. After observing the
expected assertion failure, use repeated red/green cycles to replace the
temporary test with the final construction tests below. Add each behavior test
before its corresponding implementation.

Delete the empty `tests/test_environment.py`. Create `tests/environment/test_environment.py` with:

```python
import pytest

from simulator.domain.errors import DomainValidationError
from simulator.domain.ru import RUStatus
from simulator.environment import (
    Environment,
    EnvironmentConfig,
    MapConfig,
    RUConfig,
)


def make_config(
    *,
    width: int = 4,
    height: int = 3,
    ru_count: int = 2,
    user_count: int = 3,
    initial_battery: float = 100.0,
    initial_status: RUStatus = RUStatus.ACTIVE,
    active_consumption: float = 2.0,
    sleep_consumption: float = 0.5,
    coverage_radius: float = 4.0,
    random_seed: int | None = 7,
) -> EnvironmentConfig:
    return EnvironmentConfig(
        map=MapConfig(width=width, height=height),
        ru=RUConfig(
            count=ru_count,
            initial_battery=initial_battery,
            initial_status=initial_status,
            active_consumption=active_consumption,
            sleep_consumption=sleep_consumption,
            coverage_radius=coverage_radius,
        ),
        user_count=user_count,
        random_seed=random_seed,
    )


def placement_signature(environment: Environment) -> tuple[tuple[int, int, int], ...]:
    ru_locations = sorted(
        (
            (ru.id, cell.x, cell.y)
            for ru, cell in environment.get_ru_locations().items()
        )
    )
    user_locations = sorted(
        (
            (user.id, cell.x, cell.y)
            for user, cell in environment.get_user_locations().items()
        )
    )
    return tuple(ru_locations + user_locations)


def test_creates_row_major_map() -> None:
    environment = Environment(make_config(width=4, height=3))

    environment_map = environment.get_map()
    assert len(environment_map) == 3
    assert all(len(row) == 4 for row in environment_map)
    for y, row in enumerate(environment_map):
        for x, cell in enumerate(row):
            assert (cell.x, cell.y) == (x, y)


def test_creates_uniform_rus_and_sequential_entity_ids() -> None:
    environment = Environment(
        make_config(
            ru_count=2,
            user_count=3,
            initial_battery=80.0,
            initial_status=RUStatus.SLEEP,
            active_consumption=3.0,
            sleep_consumption=0.25,
        )
    )

    rus = environment.get_rus()
    users = environment.get_users()
    assert [ru.id for ru in rus] == [1, 2]
    assert [user.id for user in users] == [1, 2, 3]
    for ru in rus:
        assert ru.get_battery() == 80.0
        assert ru.get_initial_capacity() == 80.0
        assert ru.get_status() is RUStatus.SLEEP
        assert ru.active_consumption == 3.0
        assert ru.sleep_consumption == 0.25


def test_places_every_entity_in_one_distinct_cell() -> None:
    environment = Environment(make_config())

    occupied_cells = [
        cell
        for row in environment.get_map()
        for cell in row
        if cell.occupant is not None
    ]
    assert len(occupied_cells) == 5
    assert len({(cell.x, cell.y) for cell in occupied_cells}) == 5

    environment_map = environment.get_map()
    for ru, cell in environment.get_ru_locations().items():
        assert cell.occupant is ru
        assert environment_map[cell.y][cell.x] is cell
    for user, cell in environment.get_user_locations().items():
        assert cell.occupant is user
        assert environment_map[cell.y][cell.x] is cell


def test_equal_seeds_reproduce_placements() -> None:
    first = Environment(make_config(random_seed=19))
    second = Environment(make_config(random_seed=19))

    assert placement_signature(first) == placement_signature(second)


def test_collection_getters_protect_environment_structure() -> None:
    environment = Environment(make_config())

    returned_map = environment.get_map()
    returned_map[0].clear()
    returned_rus = environment.get_rus()
    returned_rus.clear()
    returned_users = environment.get_users()
    returned_users.clear()
    returned_ru_locations = environment.get_ru_locations()
    returned_ru_locations.clear()
    returned_user_locations = environment.get_user_locations()
    returned_user_locations.clear()

    assert len(environment.get_map()[0]) == 4
    assert len(environment.get_rus()) == 2
    assert len(environment.get_users()) == 3
    assert len(environment.get_ru_locations()) == 2
    assert len(environment.get_user_locations()) == 3


def test_returned_ru_objects_retain_mutable_state() -> None:
    environment = Environment(make_config(initial_status=RUStatus.ACTIVE))

    environment.get_rus()[0].set_status(RUStatus.SLEEP)

    assert environment.get_rus()[0].get_status() is RUStatus.SLEEP


def test_propagates_ru_validation_for_invalid_uniform_settings() -> None:
    config = make_config(initial_battery=0.0)

    with pytest.raises(DomainValidationError, match="battery"):
        Environment(config)
```

Replace `tests/environment/test_public_imports.py` with:

```python
from simulator.environment import (
    Environment,
    EnvironmentConfig,
    EnvironmentValidationError,
    MapConfig,
    RUConfig,
)


def test_environment_types_are_publicly_importable() -> None:
    assert Environment.__name__ == "Environment"
    assert MapConfig.__name__ == "MapConfig"
    assert RUConfig.__name__ == "RUConfig"
    assert EnvironmentConfig.__name__ == "EnvironmentConfig"
    assert issubclass(EnvironmentValidationError, ValueError)
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run the temporary discovery test before creating the class:

```bash
uv run pytest tests/environment/test_environment.py::test_environment_is_publicly_available -v
```

Expected: pytest executes the test and marks it failed because
`simulator.environment` does not yet export `Environment`.

- [ ] **Step 3: Implement immediate environment construction and protected getters**

Create `src/simulator/environment/environment.py` with:

```python
import random

from simulator.domain.map_cell import MapCell
from simulator.domain.ru import RU
from simulator.domain.user import User
from simulator.environment.config import EnvironmentConfig


class Environment:
    def __init__(self, config: EnvironmentConfig) -> None:
        self._config = config
        self._random = random.Random(config.random_seed)
        self._map = self._create_map()
        self._rus = self._create_rus()
        self._users = self._create_users()
        self._ru_locations: dict[RU, MapCell] = {}
        self._user_locations: dict[User, MapCell] = {}
        self._place_entities()

    def _create_map(self) -> list[list[MapCell]]:
        return [
            [MapCell(x=x, y=y) for x in range(self._config.map.width)]
            for y in range(self._config.map.height)
        ]

    def _create_rus(self) -> list[RU]:
        config = self._config.ru
        return [
            RU(
                id=ru_id,
                battery=config.initial_battery,
                status=config.initial_status,
                active_consumption=config.active_consumption,
                sleep_consumption=config.sleep_consumption,
            )
            for ru_id in range(1, config.count + 1)
        ]

    def _create_users(self) -> list[User]:
        return [
            User(id=user_id)
            for user_id in range(1, self._config.user_count + 1)
        ]

    def _place_entities(self) -> None:
        available_cells = [cell for row in self._map for cell in row]
        entities: list[RU | User] = [*self._rus, *self._users]
        selected_cells = self._random.sample(available_cells, len(entities))

        for entity, cell in zip(entities, selected_cells, strict=True):
            occupied_cell = MapCell(x=cell.x, y=cell.y, occupant=entity)
            self._map[cell.y][cell.x] = occupied_cell
            if isinstance(entity, RU):
                self._ru_locations[entity] = occupied_cell
            else:
                self._user_locations[entity] = occupied_cell

    def get_map(self) -> list[list[MapCell]]:
        return [row.copy() for row in self._map]

    def get_rus(self) -> list[RU]:
        return self._rus.copy()

    def get_users(self) -> list[User]:
        return self._users.copy()

    def get_ru_locations(self) -> dict[RU, MapCell]:
        return self._ru_locations.copy()

    def get_user_locations(self) -> dict[User, MapCell]:
        return self._user_locations.copy()
```

Replace `src/simulator/environment/__init__.py` with:

```python
from simulator.environment.config import EnvironmentConfig, MapConfig, RUConfig
from simulator.environment.environment import Environment
from simulator.environment.errors import EnvironmentValidationError

__all__ = [
    "Environment",
    "EnvironmentConfig",
    "EnvironmentValidationError",
    "MapConfig",
    "RUConfig",
]
```

- [ ] **Step 4: Run construction tests and Ruff**

Run:

```bash
uv run pytest tests/environment/test_environment.py -v
uv run ruff check src/simulator/environment tests/environment
uv run ruff format --check src/simulator/environment tests/environment
```

Expected: construction and placement tests pass and Ruff reports no violations.

- [ ] **Step 5: Commit environment construction**

Run:

```bash
git add src/simulator/environment tests/test_environment.py tests/environment
git diff --cached --check
git commit -m "feat: construct simulation environment"
```

Expected: the commit adds complete static map/entity placement behavior without connectivity edges.

---

### Task 4: Add the Weighted NetworkX Connectivity Graph

**Files:**

- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `src/simulator/environment/environment.py`
- Create: `tests/environment/test_connectivity.py`

**Interfaces:**

- Consumes: placed RUs/users, their `MapCell` locations, `RUConfig.coverage_radius`, and the existing seeded random generator.
- Produces: `get_connectivity_graph() -> nx.Graph` and `get_connection_weight(user: User, ru: RU) -> float`.

- [ ] **Step 1: Add NetworkX through uv**

Run:

```bash
uv add networkx
```

Expected: NetworkX appears under `[project].dependencies` in `pyproject.toml`, `uv.lock` is updated, and the environment synchronizes successfully.

- [ ] **Step 2: Write failing connectivity tests**

Create `tests/environment/test_connectivity.py` with:

```python
import networkx as nx
import pytest

from simulator.domain.ru import RU, RUStatus
from simulator.domain.user import User
from simulator.environment import (
    Environment,
    EnvironmentConfig,
    MapConfig,
    RUConfig,
)


def make_environment(
    *,
    width: int = 2,
    height: int = 1,
    ru_count: int = 1,
    user_count: int = 1,
    coverage_radius: float = 2.0,
    random_seed: int = 7,
) -> Environment:
    return Environment(
        EnvironmentConfig(
            map=MapConfig(width=width, height=height),
            ru=RUConfig(
                count=ru_count,
                initial_battery=100.0,
                initial_status=RUStatus.ACTIVE,
                active_consumption=2.0,
                sleep_consumption=0.5,
                coverage_radius=coverage_radius,
            ),
            user_count=user_count,
            random_seed=random_seed,
        )
    )


def edge_weights_by_ids(environment: Environment) -> dict[tuple[int, int], float]:
    graph = environment.get_connectivity_graph()
    return {
        (ru.id, user.id): graph[ru][user]["weight"]
        for ru in environment.get_rus()
        for user in environment.get_users()
        if graph.has_edge(ru, user)
    }


def test_builds_undirected_bipartite_graph() -> None:
    environment = make_environment()
    ru = environment.get_rus()[0]
    user = environment.get_users()[0]

    graph = environment.get_connectivity_graph()
    assert isinstance(graph, nx.Graph)
    assert not graph.is_directed()
    assert set(graph.nodes) == {ru, user}
    assert graph.nodes[ru]["bipartite"] == 0
    assert graph.nodes[user]["bipartite"] == 1
    assert graph.has_edge(ru, user)
    assert graph[ru][user]["weight"] == graph[user][ru]["weight"]


@pytest.mark.parametrize("coverage_radius", [1.0, 0.5])
def test_excludes_pairs_at_or_beyond_coverage_radius(
    coverage_radius: float,
) -> None:
    environment = make_environment(coverage_radius=coverage_radius)
    ru = environment.get_rus()[0]
    user = environment.get_users()[0]

    graph = environment.get_connectivity_graph()
    assert set(graph.nodes) == {ru, user}
    assert graph.number_of_edges() == 0
    assert environment.get_connection_weight(user, ru) == 0.0


def test_connected_weight_is_positive_and_bounded_by_closeness() -> None:
    environment = make_environment(coverage_radius=2.0)
    ru = environment.get_rus()[0]
    user = environment.get_users()[0]
    distance = environment.get_ru_locations()[ru].distance_to(
        environment.get_user_locations()[user]
    )
    closeness = 1 - distance / 2.0

    weight = environment.get_connection_weight(user, ru)

    assert 0.0 < weight <= closeness


def test_graph_contains_only_ru_to_user_edges() -> None:
    environment = make_environment(
        width=3,
        height=2,
        ru_count=2,
        user_count=2,
        coverage_radius=10.0,
    )

    for left, right in environment.get_connectivity_graph().edges:
        assert {type(left), type(right)} == {RU, User}


def test_equal_seeds_reproduce_connection_weights() -> None:
    first = make_environment(
        width=3,
        height=2,
        ru_count=2,
        user_count=2,
        coverage_radius=10.0,
        random_seed=19,
    )
    second = make_environment(
        width=3,
        height=2,
        ru_count=2,
        user_count=2,
        coverage_radius=10.0,
        random_seed=19,
    )

    assert edge_weights_by_ids(first) == edge_weights_by_ids(second)


def test_graph_getter_returns_independent_graph_copy() -> None:
    environment = make_environment()
    returned_graph = environment.get_connectivity_graph()
    returned_graph.clear()

    internal_copy = environment.get_connectivity_graph()
    assert internal_copy.number_of_nodes() == 2
    assert internal_copy.number_of_edges() == 1


def test_foreign_entities_have_no_connection() -> None:
    environment = make_environment()
    owned_ru = environment.get_rus()[0]
    owned_user = environment.get_users()[0]
    foreign_user_with_same_id = User(id=owned_user.id)
    foreign_ru_with_same_id = RU(
        id=owned_ru.id,
        battery=100.0,
        status=RUStatus.ACTIVE,
        active_consumption=2.0,
        sleep_consumption=0.5,
    )

    assert (
        environment.get_connection_weight(foreign_user_with_same_id, owned_ru)
        == 0.0
    )
    assert (
        environment.get_connection_weight(owned_user, foreign_ru_with_same_id)
        == 0.0
    )
```

- [ ] **Step 3: Run connectivity tests to verify they fail**

Run:

```bash
uv run pytest tests/environment/test_connectivity.py -v
```

Expected: tests fail because `Environment` has no connectivity graph getter or connection-weight lookup.

- [ ] **Step 4: Implement graph construction and lookup**

Replace `src/simulator/environment/environment.py` with:

```python
import random

import networkx as nx

from simulator.domain.map_cell import MapCell
from simulator.domain.ru import RU
from simulator.domain.user import User
from simulator.environment.config import EnvironmentConfig


class Environment:
    def __init__(self, config: EnvironmentConfig) -> None:
        self._config = config
        self._random = random.Random(config.random_seed)
        self._map = self._create_map()
        self._rus = self._create_rus()
        self._users = self._create_users()
        self._ru_locations: dict[RU, MapCell] = {}
        self._user_locations: dict[User, MapCell] = {}
        self._place_entities()
        self._connectivity_graph = self._create_connectivity_graph()

    def _create_map(self) -> list[list[MapCell]]:
        return [
            [MapCell(x=x, y=y) for x in range(self._config.map.width)]
            for y in range(self._config.map.height)
        ]

    def _create_rus(self) -> list[RU]:
        config = self._config.ru
        return [
            RU(
                id=ru_id,
                battery=config.initial_battery,
                status=config.initial_status,
                active_consumption=config.active_consumption,
                sleep_consumption=config.sleep_consumption,
            )
            for ru_id in range(1, config.count + 1)
        ]

    def _create_users(self) -> list[User]:
        return [
            User(id=user_id)
            for user_id in range(1, self._config.user_count + 1)
        ]

    def _place_entities(self) -> None:
        available_cells = [cell for row in self._map for cell in row]
        entities: list[RU | User] = [*self._rus, *self._users]
        selected_cells = self._random.sample(available_cells, len(entities))

        for entity, cell in zip(entities, selected_cells, strict=True):
            occupied_cell = MapCell(x=cell.x, y=cell.y, occupant=entity)
            self._map[cell.y][cell.x] = occupied_cell
            if isinstance(entity, RU):
                self._ru_locations[entity] = occupied_cell
            else:
                self._user_locations[entity] = occupied_cell

    def _create_connectivity_graph(self) -> nx.Graph:
        graph = nx.Graph()
        graph.add_nodes_from(self._rus, bipartite=0)
        graph.add_nodes_from(self._users, bipartite=1)

        coverage_radius = self._config.ru.coverage_radius
        for ru in self._rus:
            for user in self._users:
                distance = self._ru_locations[ru].distance_to(
                    self._user_locations[user]
                )
                if distance >= coverage_radius:
                    continue

                closeness = 1 - distance / coverage_radius
                random_factor = 1 - self._random.random()
                graph.add_edge(ru, user, weight=random_factor * closeness)

        return graph

    def get_map(self) -> list[list[MapCell]]:
        return [row.copy() for row in self._map]

    def get_rus(self) -> list[RU]:
        return self._rus.copy()

    def get_users(self) -> list[User]:
        return self._users.copy()

    def get_ru_locations(self) -> dict[RU, MapCell]:
        return self._ru_locations.copy()

    def get_user_locations(self) -> dict[User, MapCell]:
        return self._user_locations.copy()

    def get_connectivity_graph(self) -> nx.Graph:
        return self._connectivity_graph.copy()

    def get_connection_weight(self, user: User, ru: RU) -> float:
        owns_user = any(candidate is user for candidate in self._users)
        owns_ru = any(candidate is ru for candidate in self._rus)
        if not owns_user or not owns_ru:
            return 0.0

        edge = self._connectivity_graph.get_edge_data(user, ru)
        if edge is None:
            return 0.0
        return float(edge["weight"])
```

- [ ] **Step 5: Run all environment tests and Ruff**

Run:

```bash
uv run pytest tests/environment -v
uv run ruff check src/simulator/environment tests/environment
uv run ruff format --check src/simulator/environment tests/environment
```

Expected: all environment tests pass and Ruff reports no violations.

- [ ] **Step 6: Commit NetworkX connectivity**

Run:

```bash
git add pyproject.toml uv.lock src/simulator/environment/environment.py tests/environment/test_connectivity.py
git diff --cached --check
git commit -m "feat: add environment connectivity graph"
```

Expected: the commit includes NetworkX, the locked dependency, graph behavior, and focused tests.

---

### Task 5: Update Documentation and Verify the Feature

**Files:**

- Modify: `README.md`
- Modify: `AGENTS.md`
- Verify: all changed source, tests, dependency files, design, and plan

**Interfaces:**

- Consumes: the completed `MapCell`, configuration, `Environment`, and graph API.
- Produces: accurate user-facing documentation and final verification evidence.

- [ ] **Step 1: Replace README content with the implemented environment documentation**

Replace `README.md` with:

```markdown
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
```

- [ ] **Step 2: Update the repository-layout reference in AGENTS.md**

Replace this line:

```markdown
- `src/simulator/domain/`: core simulation objects such as `Point`, `RU`, and `User`
```

with:

```markdown
- `src/simulator/domain/`: core simulation objects such as `MapCell`, `RU`, and `User`
```

Replace this line:

```markdown
- `src/simulator/environment.py`: ownership of entities and complete simulation state
```

with:

```markdown
- `src/simulator/environment/`: configuration and ownership of complete simulation state
```

- [ ] **Step 3: Run the full verification set**

Run:

```bash
uv sync --dev
uv run pytest
uv run ruff check .
uv run ruff format --check .
git diff --check
```

Expected: the environment synchronizes, all tests pass, Ruff reports no lint or formatting errors, and Git reports no whitespace errors.

- [ ] **Step 4: Inspect final scope and commit documentation**

Run:

```bash
git status --short
git diff --stat
git diff -- README.md AGENTS.md
git add README.md AGENTS.md
git diff --cached --check
git commit -m "docs: document simulation environment"
```

Expected: only intended environment changes are present, and the final documentation commit succeeds.

- [ ] **Step 5: Record final branch verification**

Run:

```bash
git status --short --branch
git log --oneline --decorate -6
```

Expected: `feat/environment` is clean and contains the design, domain, configuration, construction, connectivity, and documentation commits.
