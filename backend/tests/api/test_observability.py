import json
import logging
import re

from fastapi.testclient import TestClient

from app.main import create_app
from app.observability import configure_logging, workflow_log


def _payload(record: logging.LogRecord) -> dict[str, object]:
    return json.loads(re.sub(r"\x1b\[[0-9;]*m", "", record.getMessage()))


def test_workflow_log_redacts_content_bearing_fields() -> None:
    logger = configure_logging()
    records: list[logging.LogRecord] = []

    class Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    capture = Capture()
    logger.addHandler(capture)
    try:
        workflow_log(
            "SOURCE",
            "SOURCE_CREATED",
            sourceId="source-1",
            transcript_text="must not appear",
            sourceText="must not appear",
            accessToken="must not appear",
        )
    finally:
        logger.removeHandler(capture)

    payload = _payload(records[-1])
    assert payload == {"event": "SOURCE_CREATED", "operation": "SOURCE", "sourceId": "source-1"}


def test_request_middleware_emits_start_and_success_lifecycle_logs() -> None:
    logger = configure_logging()
    records: list[logging.LogRecord] = []

    class Capture(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    capture = Capture()
    logger.addHandler(capture)
    try:
        response = TestClient(create_app()).get("/api/v1/health", headers={"x-request-id": "request-observability-test"})
    finally:
        logger.removeHandler(capture)

    assert response.status_code == 200
    events = [_payload(record) for record in records]
    assert {event["event"] for event in events} >= {"HTTP_REQUEST_STARTED", "HTTP_REQUEST_COMPLETED"}
    completed = next(event for event in events if event["event"] == "HTTP_REQUEST_COMPLETED")
    assert completed["requestId"] == "request-observability-test"
    assert completed["statusCode"] == 200
    assert completed["outcome"] == "SUCCESS"
