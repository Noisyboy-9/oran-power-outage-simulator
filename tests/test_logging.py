import logging
import sys

import structlog

from simulator.configuration import LoggingConfig, TimestampConfig
from simulator.logging import configure_logging


def test_configure_logging_applies_configured_logger_settings() -> None:
    config = LoggingConfig(
        logger_name="simulator.tests.logging",
        level=logging.WARNING,
        destination="stdout",
        format="json",
        include_logger_name=True,
        include_log_level=True,
        timestamp=TimestampConfig(key="emitted_at", format="iso", utc=True),
        cache_loggers_on_first_use=False,
        propagate=True,
    )

    configure_logging(config)

    logger = logging.getLogger(config.logger_name)
    assert logger.level == logging.WARNING
    assert logger.propagate is True
    assert len(logger.handlers) == 1
    assert logger.handlers[0].stream is sys.stdout

    logger.handlers[0].close()
    logger.handlers.clear()
    structlog.reset_defaults()
