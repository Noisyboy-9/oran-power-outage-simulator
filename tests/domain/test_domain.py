from simulator.domain import RU, DomainValidationError, Point, RUStatus, User


def test_domain_types_are_publicly_importable() -> None:
    assert Point.__name__ == "Point"
    assert User.__name__ == "User"
    assert RU.__name__ == "RU"
    assert RUStatus.__name__ == "RUStatus"
    assert issubclass(DomainValidationError, ValueError)
