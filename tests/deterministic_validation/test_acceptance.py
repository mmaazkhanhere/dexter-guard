from __future__ import annotations

import json
from pathlib import Path

from deterministic_validation.contracts import ValidationRun
from deterministic_validation.observability import InMemoryValidationTelemetry

from .test_service import make_service, request


MANIFEST = json.loads(
    Path("specs/005-deterministic-validation-engine/fixtures/spec005-acceptance-v1.json").read_text(encoding="utf-8")
)


def test_acceptance_manifest_covers_at001_through_at021_with_versioned_expected_results() -> None:
    case_ids = [item["id"] for item in MANIFEST["cases"]]
    assert case_ids == [f"AT-{index:03d}" for index in range(1, 22)]
    assert MANIFEST["manifestVersion"] == "SPEC005_ACCEPTANCE-v1"
    assert MANIFEST["rulesetVersion"] == "DVE-RULESET-v1"
    assert all(item.get("expected") for item in MANIFEST["cases"])


def test_repeatability_is_identical_after_removing_only_run_identifier() -> None:
    identifiers = iter(("run-1", "run-2"))
    service = make_service()
    service._id_factory = lambda: next(identifiers)
    first = service.execute(request())
    second = service.execute(request())
    first_payload = first.model_dump(mode="json", by_alias=True)
    second_payload = second.model_dump(mode="json", by_alias=True)
    first_payload.pop("validationRunId")
    second_payload.pop("validationRunId")
    assert first_payload == second_payload
    assert first.input_digest == second.input_digest


def test_telemetry_contains_only_safe_run_metadata() -> None:
    telemetry = InMemoryValidationTelemetry()
    service = make_service()
    service.telemetry = telemetry
    service.execute(request())
    event = telemetry.events[0]
    payload = event.__dict__
    assert payload["ruleset_version"] == "DVE-RULESET-v1"
    assert "transcript" not in str(payload).lower()
    assert "37,2" not in str(payload)


def test_run_contract_round_trips_canonical_json() -> None:
    run = make_service().execute(request())
    restored = ValidationRun.model_validate(run.model_dump(by_alias=True))
    assert restored == run

