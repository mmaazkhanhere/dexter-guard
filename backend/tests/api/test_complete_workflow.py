from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app
from nursing_notes.adapters import DeterministicNursingNoteAdapter


def _import_note(client: TestClient, transcript: str, suffix: str, *, content: str | None = None) -> tuple[dict, dict]:
    source_response = client.post(
        "/api/v1/sources",
        json={
            "resident_test_id": f"resident-{suffix}",
            "language": "de-DE",
            "transcript_text": transcript,
        },
    )
    assert source_response.status_code == 201
    source = source_response.json()

    note_response = client.post(
        "/api/v1/notes/import",
        json={
            "sourceId": source["source_id"],
            "sourceVersion": source["source_version"],
            "content": content or transcript,
            "externalOrigin": {"system": "complete-workflow-test", "externalNoteId": suffix},
            "requestedBy": "integration-test",
            "facts": [],
        },
    )
    assert note_response.status_code == 201
    return source, note_response.json()


def _verify(client: TestClient, note: dict, suffix: str, *, revision: int = 1):
    response = client.post(
        f"/api/v1/reviews/{note['noteId']}/full-verifications",
        json={
            "expectedRevision": revision,
            "reviewerLabel": "integration-test",
            "idempotencyKey": f"verify-{suffix}",
        },
    )
    assert response.status_code == 200
    return response.json()


def test_complete_workflow_persists_every_component_with_shared_provenance() -> None:
    app = create_app()
    client = TestClient(app)
    transcript = "Die Bewohnerin berichtet keine Schmerzen. Temperatur 37,2 C."
    source, note = _import_note(client, transcript, "persisted")

    verification = _verify(client, note, "persisted")

    assert verification["status"] == "VALID"
    assert verification["source"] == {
        "sourceId": source["source_id"],
        "sourceVersion": source["source_version"],
    }
    assert verification["coverageUnresolvedSourceItems"] == 0
    assert {item["component"] for item in verification["componentStatuses"]} == {
        "CLAIM_EXTRACTION",
        "EVIDENCE_VERIFICATION",
        "DETERMINISTIC_VALIDATION",
        "SOURCE_COVERAGE",
    }
    assert all(item["status"] == "SUCCEEDED" and item["runId"] for item in verification["componentStatuses"])

    workflow = app.state.workflow
    note_revision_id = f"{note['noteId']}:r1"
    claim_set_id = verification["claimSetId"]

    extraction = workflow.claim_service.repository.get_current_result(note_revision_id)
    assert extraction is not None
    assert extraction.extraction_run_id == claim_set_id
    assert extraction.status.value == "SUCCEEDED"
    assert extraction.claims
    assert all(claim.note_revision_id == note_revision_id for claim in extraction.claims)
    assert all(claim.resident_test_id == source["resident_test_id"] for claim in extraction.claims)

    claim_set = workflow.claim_sets._items[claim_set_id]
    assert claim_set.note_id == note["noteId"]
    assert claim_set.note_revision == 1
    assert claim_set.source_id == source["source_id"]
    assert claim_set.source_version == source["source_version"]
    assert f"source-facts-{claim_set_id}" in workflow.extraction_repository._items

    evidence_run = workflow.evidence_runs.get(verification["evidenceRunId"])
    assert evidence_run is not None
    assert getattr(evidence_run.status, "value", evidence_run.status) == "SUCCEEDED"
    assert evidence_run.source_id == source["source_id"]
    assert evidence_run.source_version == source["source_version"]
    assert evidence_run.note_id == note["noteId"]
    assert evidence_run.note_revision == 1
    assert evidence_run.claim_set_id == claim_set_id

    validation_run = next(
        run for run in workflow.validation_runs.runs if run.validation_run_id == verification["deterministicValidationRunId"]
    )
    assert validation_run.validation_run_id == verification["deterministicValidationRunId"]
    assert validation_run.source_id == source["source_id"]
    assert validation_run.source_version == source["source_version"]
    assert validation_run.note_id == note["noteId"]
    assert validation_run.note_revision == 1

    coverage_run = next(
        run for run in workflow.coverage_runs.runs if run.coverage_run_id == verification["coverageRunId"]
    )
    assert getattr(coverage_run.status, "value", coverage_run.status) == "SUCCEEDED"
    assert coverage_run.source_id == source["source_id"]
    assert coverage_run.source_version == source["source_version"]
    assert coverage_run.note_id == note["noteId"]
    assert coverage_run.note_revision == 1
    assert coverage_run.claim_set_id == claim_set_id
    assert coverage_run.runtime_counts.unresolved_source_items == 0


def test_generated_note_flows_from_ai_generation_through_review_approval() -> None:
    app = create_app()
    client = TestClient(app)
    app.state.note_service.generation_adapter = DeterministicNursingNoteAdapter()
    transcript = "Die Bewohnerin berichtet keine Schmerzen."

    source_response = client.post(
        "/api/v1/sources",
        json={
            "resident_test_id": "resident-generated-flow",
            "language": "de-DE",
            "transcript_text": transcript,
        },
    )
    assert source_response.status_code == 201
    source = source_response.json()

    generated_response = client.post(
        "/api/v1/notes/generate",
        json={
            "sourceId": source["source_id"],
            "sourceVersion": source["source_version"],
            "requestedBy": "caregiver-reviewer",
        },
    )

    assert generated_response.status_code == 201
    generated_note = generated_response.json()
    assert generated_note["origin"] == "GENERATED"
    assert generated_note["generationRunId"]
    assert generated_note["sourceId"] == source["source_id"]
    assert generated_note["sourceVersion"] == source["source_version"]
    assert app.state.note_service.generation_adapter.invocation_count == 1

    verification = _verify(client, generated_note, "generated")

    assert verification["status"] == "VALID"
    assert all(item["status"] == "SUCCEEDED" for item in verification["componentStatuses"])

    context = client.get(f"/api/v1/reviews/{generated_note['noteId']}")
    assert context.status_code == 200
    assert context.json()["approvalEligible"] is True

    approval = client.post(
        f"/api/v1/reviews/{generated_note['noteId']}/approve",
        json={
            "expectedRevision": 1,
            "reviewerLabel": "caregiver-reviewer",
            "fullVerificationId": verification["fullVerificationId"],
            "idempotencyKey": "approve-generated",
        },
    )

    assert approval.status_code == 201


def test_caregiver_revision_is_saved_to_main_store_and_can_be_reverified_and_approved() -> None:
    app = create_app()
    client = TestClient(app)
    transcript = "Die Bewohnerin berichtet keine Schmerzen."
    source, note = _import_note(client, transcript, "revision-sync")

    edit = client.post(
        f"/api/v1/reviews/{note['noteId']}/revisions",
        json={
            "expectedRevision": 1,
            "content": f"{transcript} ",
            "reviewerLabel": "caregiver-reviewer",
            "idempotencyKey": "revision-sync-edit",
        },
    )

    assert edit.status_code == 201
    edit_body = edit.json()
    assert edit_body["noteId"] == note["noteId"]
    assert edit_body["revision"] == 2
    assert edit_body["previousRevision"] == 1
    assert edit_body["noteStatus"] == "AWAITING_FULL_VERIFICATION"
    assert edit_body["auditEventId"]
    assert app.state.note_service.repository.get(note["noteId"], 2).content == f"{transcript} "
    assert app.state.review_service.get_note(note["noteId"], 2).content == f"{transcript} "

    verification = _verify(client, note, "revision-sync-verify", revision=2)

    assert verification["status"] == "VALID"
    assert verification["noteRevision"] == 2
    context = client.get(f"/api/v1/reviews/{note['noteId']}")
    assert context.status_code == 200
    assert context.json()["revision"] == 2
    assert context.json()["approvalEligible"] is True

    approval = client.post(
        f"/api/v1/reviews/{note['noteId']}/approve",
        json={
            "expectedRevision": 2,
            "reviewerLabel": "caregiver-reviewer",
            "fullVerificationId": verification["fullVerificationId"],
            "idempotencyKey": "revision-sync-approve",
        },
    )

    assert approval.status_code == 201


def test_review_context_exposes_validation_and_coverage_details() -> None:
    app = create_app()
    client = TestClient(app)
    source_text = "Die Bewohnerin berichtet eine Temperatur von 37,2 C."
    note_text = "Die Bewohnerin berichtet eine Temperatur von 39,2 C."
    _, note = _import_note(client, source_text, "findings", content=note_text)

    verification = _verify(client, note, "findings")
    context = client.get(f"/api/v1/reviews/{note['noteId']}")

    assert verification["status"] == "VALID"
    assert context.status_code == 200
    body = context.json()
    findings = body["findings"]
    origins = {finding["origin"] for finding in findings}

    assert {"SPEC_004", "SPEC_005", "SPEC_006"}.issubset(origins)
    validation_finding = next(finding for finding in findings if finding["origin"] == "SPEC_005")
    assert validation_finding["ruleCode"].startswith("NUM-")
    assert "Expected:" in validation_finding["explanation"]
    assert "observed:" in validation_finding["explanation"]
    coverage_finding = next(finding for finding in findings if finding["origin"] == "SPEC_006")
    assert coverage_finding["evidence"]["availability"] == "AVAILABLE"
    assert coverage_finding["evidence"]["excerpts"]
    assert body["approvalEligible"] is False


def test_missing_note_measurement_fails_closed_instead_of_skipping_numeric_validation() -> None:
    app = create_app()
    client = TestClient(app)
    source_text = "Die Bewohnerin berichtet eine Temperatur von 37,2 C."
    note_text = "Die Bewohnerin berichtet eine normale Temperatur."
    _, note = _import_note(client, source_text, "missing-number", content=note_text)

    verification = _verify(client, note, "missing-number")
    context = client.get(f"/api/v1/reviews/{note['noteId']}")

    assert verification["status"] == "FAILED"
    validation_status = next(
        item for item in verification["componentStatuses"] if item["component"] == "DETERMINISTIC_VALIDATION"
    )
    assert validation_status["status"] == "FAILED"
    assert context.status_code == 200
    finding = next(
        item for item in context.json()["findings"]
        if item["origin"] == "SPEC_005" and item["ruleCode"] == "NUM-006"
    )
    assert finding["upstreamStatus"] == "NOT_EVALUABLE"
    assert "37.2" in finding["explanation"] or "37,2" in finding["explanation"]
    assert finding["evidence"]["availability"] == "AVAILABLE"
    assert context.json()["approvalEligible"] is False


def test_compound_vital_signs_preserve_pulse_for_numeric_validation() -> None:
    app = create_app()
    client = TestClient(app)
    source_text = "Die Temperatur betr\u00e4gt 37,2 C und der Puls liegt bei 83 Schl\u00e4gen pro Minute."
    note_text = "Die Temperatur betr\u00e4gt 37,2 C und der Puls liegt bei 110 Schl\u00e4gen pro Minute."
    _, note = _import_note(client, source_text, "pulse-mismatch", content=note_text)

    verification = _verify(client, note, "pulse-mismatch")
    context = client.get(f"/api/v1/reviews/{note['noteId']}")

    assert verification["status"] == "VALID"
    assert context.status_code == 200
    numeric = next(
        item for item in context.json()["findings"]
        if item["origin"] == "SPEC_005" and item["ruleCode"] == "NUM-001"
    )
    assert "Expected: 83; observed: 110." in numeric["explanation"]
    assert context.json()["approvalEligible"] is False


def test_complete_workflow_calls_real_components_in_order(monkeypatch) -> None:
    app = create_app()
    client = TestClient(app)
    source, note = _import_note(
        client,
        "Die Bewohnerin berichtet keine Schmerzen. Temperatur 37,2 C.",
        "order",
    )
    workflow = app.state.workflow
    events: list[str] = []

    def wrap(service, method_name: str, label: str) -> None:
        original = getattr(service, method_name)

        def wrapped(*args, **kwargs):
            events.append(label)
            return original(*args, **kwargs)

        monkeypatch.setattr(service, method_name, wrapped)

    wrap(workflow.claim_service, "extract_claims", "CLAIM_EXTRACTION")
    wrap(workflow.evidence_service, "verify", "EVIDENCE_VERIFICATION")
    wrap(workflow.validation_service, "execute", "DETERMINISTIC_VALIDATION")
    wrap(workflow.coverage_service, "execute", "SOURCE_COVERAGE")

    verification = _verify(client, note, "order")

    assert verification["status"] == "VALID"
    assert events == [
        "CLAIM_EXTRACTION",
        "EVIDENCE_VERIFICATION",
        "DETERMINISTIC_VALIDATION",
        "SOURCE_COVERAGE",
    ]
    assert verification["source"] == {
        "sourceId": source["source_id"],
        "sourceVersion": source["source_version"],
    }


def test_unresolved_source_item_blocks_approval_in_composed_workflow() -> None:
    app = create_app()
    client = TestClient(app)
    _, note = _import_note(client, "Die Situation bleibt unklar.", "blocked")

    verification = _verify(client, note, "blocked")

    assert verification["status"] == "INVALID"
    assert verification["failureCode"] == "UNRESOLVED_SOURCE_ITEM"
    assert verification["coverageUnresolvedSourceItems"] > 0
    assert all(item["status"] == "SUCCEEDED" for item in verification["componentStatuses"])

    approval = client.post(
        f"/api/v1/reviews/{note['noteId']}/approve",
        json={
            "expectedRevision": 1,
            "reviewerLabel": "integration-test",
            "fullVerificationId": verification["fullVerificationId"],
            "idempotencyKey": "approve-blocked",
        },
    )

    assert approval.status_code == 409
    assert approval.json()["code"] == "APPROVAL_PRECONDITION_FAILED"

    context = client.get(f"/api/v1/reviews/{note['noteId']}")
    assert context.status_code == 200
    assert context.json()["approvalEligible"] is False
