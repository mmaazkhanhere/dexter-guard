import pytest

from evaluation import cli


def test_live_cli_fails_closed_without_configured_verifier(monkeypatch) -> None:
    monkeypatch.delenv("VERIFICATION_LLM_API_KEY", raising=False)
    monkeypatch.delenv("VERIFICATION_LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)

    with pytest.raises(SystemExit) as error:
        cli.main(["--split", "HELD_OUT", "--database", ":memory:"])

    assert error.value.code == 2
