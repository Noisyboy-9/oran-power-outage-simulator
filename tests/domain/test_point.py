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
