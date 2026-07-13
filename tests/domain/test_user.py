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
