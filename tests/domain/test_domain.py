import simulator.domain as domain
from simulator.domain import RU, DomainValidationError, MapCell, RUStatus, User


def test_domain_types_are_publicly_importable() -> None:
    assert MapCell.__name__ == "MapCell"
    assert User.__name__ == "User"
    assert RU.__name__ == "RU"
    assert RUStatus.__name__ == "RUStatus"
    assert issubclass(DomainValidationError, ValueError)
    assert not hasattr(domain, "Point")
