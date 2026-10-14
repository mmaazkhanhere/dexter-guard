"""Content-minimized, colour-coded operational logging for the API boundary.

Logs deliberately contain workflow metadata only.  Nursing documentation,
claims, source spans, prompts, model output, credentials, and request bodies
must never be emitted here.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from collections.abc import Mapping
from contextlib import contextmanager
from time import perf_counter
from typing import Iterator

from colorama import Fore, Style, init


_LOGGER_NAME = "dexter_guard.workflow"
_FORBIDDEN_FIELDS = frozenset(
    {
        "content",
        "source_text",
        "transcript",
        "transcript_text",
        "note",
        "note_text",
        "claim",
        "claim_text",
        "prompt",
        "raw_output",
        "replacement",
        "authorization",
        "password",
        "secret",
        "token",
        "api_key",
    }
)
_SECRET_FIELD_MARKERS = ("authorization", "password", "secret", "token", "apikey")
_OPERATION_COLOURS = {
    "REQUEST": Fore.BLUE,
    "SOURCE": Fore.CYAN,
    "NOTE": Fore.MAGENTA,
    "CLAIM_EXTRACTION": Fore.LIGHTBLUE_EX,
    "EVIDENCE_VERIFICATION": Fore.LIGHTMAGENTA_EX,
    "DETERMINISTIC_VALIDATION": Fore.LIGHTYELLOW_EX,
    "SOURCE_COVERAGE": Fore.LIGHTCYAN_EX,
    "HUMAN_REVIEW": Fore.WHITE,
    "EVALUATION": Fore.LIGHTWHITE_EX,
    "HEALTH": Fore.YELLOW,
}


def configure_logging() -> logging.Logger:
    """Return the dedicated workflow logger configured once for console output."""

    init(autoreset=True)
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    return logger


def _safe_fields(fields: Mapping[str, object]) -> dict[str, object]:
    safe: dict[str, object] = {}
    forbidden = {re.sub(r"[^a-z0-9]", "", key.casefold()) for key in _FORBIDDEN_FIELDS}
    for key, value in fields.items():
        normalized_key = re.sub(r"[^a-z0-9]", "", key.casefold())
        if normalized_key in forbidden or any(marker in normalized_key for marker in _SECRET_FIELD_MARKERS):
            continue
        safe[key] = value
    return safe


def workflow_log(operation: str, event: str, /, **fields: object) -> None:
    """Emit one structured, safe log line with semantic console colouring."""

    safe_fields = _safe_fields(fields)
    payload = {"operation": operation, "event": event, **safe_fields}
    outcome = str(safe_fields.get("outcome", "")).upper()
    status_code = safe_fields.get("statusCode")
    is_error = outcome == "ERROR" or (isinstance(status_code, int) and status_code >= 400)
    is_success = outcome == "SUCCESS" or (isinstance(status_code, int) and 200 <= status_code < 400)
    colour = Fore.RED if is_error else Fore.GREEN if is_success else _OPERATION_COLOURS.get(operation, Fore.WHITE)
    configure_logging().info("%s%s%s", colour, json.dumps(payload, default=str, sort_keys=True), Style.RESET_ALL)


@contextmanager
def workflow_step(operation: str, event: str, /, **fields: object) -> Iterator[None]:
    """Log a bounded workflow step and its terminal result without contents."""

    started = perf_counter()
    workflow_log(operation, f"{event}_STARTED", **fields)
    try:
        yield
    except Exception as error:
        workflow_log(
            operation,
            f"{event}_FAILED",
            outcome="ERROR",
            errorType=type(error).__name__,
            latencyMs=round((perf_counter() - started) * 1000, 2),
            **fields,
        )
        raise
    else:
        workflow_log(
            operation,
            f"{event}_COMPLETED",
            outcome="SUCCESS",
            latencyMs=round((perf_counter() - started) * 1000, 2),
            **fields,
        )
