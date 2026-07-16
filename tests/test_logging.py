import json
from datetime import datetime

import structlog

from simulator.logging import configure_logging


def test_emits_info_event_as_json(capsys) -> None:
    configure_logging()
    logger = structlog.get_logger("simulator.test")

    logger.info("simulation_started", run_id=7)

    event = json.loads(capsys.readouterr().out)
    assert event["event"] == "simulation_started"
    assert event["run_id"] == 7
    assert event["level"] == "info"
    assert event["logger"] == "simulator.test"
    assert datetime.fromisoformat(event["timestamp"]).tzinfo is not None


def test_filters_debug_event(capsys) -> None:
    configure_logging()
    logger = structlog.get_logger("simulator.test")

    logger.debug("simulation_details")

    assert capsys.readouterr().out == ""
