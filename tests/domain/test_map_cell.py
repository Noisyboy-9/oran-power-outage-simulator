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
        zero_user_consumption=1.0,
        one_user_consumption=2.0,
        multi_user_consumption_per_user=1.5,
        sleep_consumption=0.5,
        user_capacity=100,
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
