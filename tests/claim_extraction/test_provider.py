import json

import pytest

from claim_extraction.provider import MalformedProviderOutputError, parse_provider_output


def test_provider_parser_accepts_json_envelope_without_calling_network() -> None:
    assert parse_provider_output(json.dumps({"claims": [{"id": "c1"}]})) == ({"id": "c1"},)


@pytest.mark.parametrize(
    "payload",
    [
        "not json",
        {"claims": "not-an-array"},
        {"claims": [], "evidence": "forbidden"},
    ],
)
def test_provider_parser_rejects_malformed_or_out_of_contract_payloads(payload: object) -> None:
    with pytest.raises(MalformedProviderOutputError):
        parse_provider_output(payload)
