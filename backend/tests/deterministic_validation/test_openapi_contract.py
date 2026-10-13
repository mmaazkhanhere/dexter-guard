from __future__ import annotations

from pathlib import Path

import yaml


def test_published_openapi_contract_matches_versioned_rule_surface() -> None:
    document = yaml.safe_load(Path("specs/005-deterministic-validation-engine/contracts/deterministic-validation.openapi.yaml").read_text(encoding="utf-8"))
    path = document["paths"]["/api/v1/deterministic-validation-runs"]["post"]
    assert path["operationId"] == "createDeterministicValidationRun"
    schemas = document["components"]["schemas"]
    request = schemas["ValidationRequest"]
    assert request["required"] == ["sourceId", "sourceVersion", "noteId", "noteRevision", "sourceFactIds", "claimIds", "alignmentIds", "rulesetVersion"]
    finding = schemas["ValidationFinding"]
    assert finding["properties"]["rulesetVersion"]["const"] == "DVE-RULESET-v1"
    assert finding["properties"]["requiresReview"]["const"] is True
    assert finding["properties"]["outcome"]["enum"] == ["FAIL", "NOT_EVALUABLE"]
    assert schemas["ValidationRun"]["properties"]["contractVersion"]["const"] == "DVE-CONTRACT-v1"

