import logging
import sys

import structlog

from simulator.configuration.models import LoggingConfig


def configure_logging(config: LoggingConfig) -> None:
    handler = logging.StreamHandler({"stdout": sys.stdout}[config.destination])
    handler.setFormatter(logging.Formatter("%(message)s"))

    simulator_logger = logging.getLogger(config.logger_name)
    for existing_handler in simulator_logger.handlers:
        existing_handler.close()
    simulator_logger.handlers = [handler]
    simulator_logger.setLevel(config.level)
    simulator_logger.propagate = config.propagate

    processors: list[structlog.types.Processor] = [structlog.stdlib.filter_by_level]
    if config.include_logger_name:
        processors.append(structlog.stdlib.add_logger_name)
    if config.include_log_level:
        processors.append(structlog.stdlib.add_log_level)
    processors.extend(
        [
            structlog.processors.TimeStamper(
                fmt=config.timestamp.format,
                utc=config.timestamp.utc,
                key=config.timestamp.key,
            ),
            {"json": structlog.processors.JSONRenderer()}[config.format],
        ]
    )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=config.cache_loggers_on_first_use,
    )
