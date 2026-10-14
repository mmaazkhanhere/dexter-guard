from starlette.testclient import TestClient

from app.main import create_app
try:
    from backend.tests.api.test_complete_workflow import _import_note, _verify
except ModuleNotFoundError:
    from tests.api.test_complete_workflow import _import_note, _verify


def test_equivalent_units_are_compared_deterministically():
    client = TestClient(create_app())
    _, note = _import_note(
        client,
        "Die Bewohnerin trank 1 L.",
        "unit-conversion",
        content="Die Bewohnerin trank 1000 ml.",
    )

    verification = _verify(client, note, "unit-conversion")

    validation = next(
        component
        for component in verification["componentStatuses"]
        if component["component"] == "DETERMINISTIC_VALIDATION"
    )
    assert validation["status"] == "SUCCEEDED"

    context = client.get(f"/api/v1/reviews/{note['noteId']}").json()
    numeric_findings = [
        finding
        for finding in context["findings"]
        if finding["origin"] == "SPEC_005"
        and finding["ruleCode"].startswith("NUM-")
    ]
    assert numeric_findings == []
