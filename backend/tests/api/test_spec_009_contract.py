from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from app.main import create_app


CONTRACT = Path(__file__).parents[3] / "specs" / "009-ui-implementation" / "contracts" / "openapi.yaml"


def _runtime_path(path: str) -> str:
    return (
        path.replace("{sourceId}", "{source_id}")
        .replace("{sourceVersion}", "{source_version}")
        .replace("{noteId}", "{note_id}")
        .replace("{noteRevision}", "{revision}")
        .replace("{findingId}", "{finding_id}")
    )


def test_confirmed_spec_009_paths_exist_in_composed_openapi() -> None:
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    confirmed = {
        _runtime_path(path)
        for path, methods in contract["paths"].items()
        if any(
            method_data.get("x-integration-status", "").startswith("confirmed")
            for method, method_data in methods.items()
            if method in {"get", "post", "put", "patch", "delete"}
        )
    }
    actual = set(TestClient(create_app()).app.openapi()["paths"])

    assert confirmed <= actual


def test_proposed_contract_routes_are_explicitly_labelled() -> None:
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    proposed = {
        path
        for path, methods in contract["paths"].items()
        if any(
            method_data.get("x-integration-status", "").startswith("proposed")
            for method, method_data in methods.items()
            if method in {"get", "post", "put", "patch", "delete"}
        )
    }

    assert "/api/v1/claims/extract" in proposed
    assert "/api/v1/verification-runs/{verificationRunId}" in proposed
