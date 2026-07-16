import logging
import sys

import structlog

_LOGGER_NAME = "simulator"


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))

    simulator_logger = logging.getLogger(_LOGGER_NAME)
    for existing_handler in simulator_logger.handlers:
        existing_handler.close()
    simulator_logger.handlers = [handler]
    simulator_logger.setLevel(logging.INFO)
    simulator_logger.propagate = False

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="logged_at"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )
