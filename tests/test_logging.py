import simulator.logging


def test_logging_is_a_package_that_exposes_configure_logging() -> None:
    assert hasattr(simulator.logging, "__path__")
    assert callable(simulator.logging.configure_logging)
