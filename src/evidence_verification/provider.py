"""Untrusted, structured semantic-verifier boundary for Spec 004.

The provider adapter deliberately contains no persistence or approval behavior.  A
provider may return a Python object, JSON text, or a Pydantic response; all forms
cross the same strict schema boundary before the application can use them.
"""

from __future__ import annotations

import inspect
import json
from collections.abc import Mapping, Sequence
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, StrictStr, ValidationError

from .contracts import (
    ANNOTATION_POLICY_VERSION,
    Discrepancy,
    EvidenceRole,
    EvidenceStatus,
    SourceSpan,
)


class VerifierError(RuntimeError):
    """Base error for provider execution or response parsing."""


class ProviderTimeoutError(VerifierError):
    pass


class ProviderUnavailableError(VerifierError):
    pass


class MalformedVerifierOutputError(VerifierError):
    pass


class VerifierCandidateFinding(BaseModel):
    """Strict model output for one claim.

    Evidence quotations are accepted only to detect provider disagreement.  The
    service always derives the authoritative quote from the immutable source.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True, str_strip_whitespace=False)

    claim_id: StrictStr = Field(alias="claimId", min_length=1)
    status: EvidenceStatus
    explanation: StrictStr = Field(min_length=1)
    source_spans: tuple[SourceSpan, ...] = Field(default_factory=tuple, alias="sourceSpans")
    evidence_quotes: tuple["VerifierEvidenceQuote", ...] = Field(default_factory=tuple, alias="evidenceQuotes")
    discrepancies: tuple[Discrepancy, ...] = Field(default_factory=tuple)


class VerifierEvidenceQuote(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True, str_strip_whitespace=False)

    span: SourceSpan
    text: StrictStr = Field(min_length=1)
    evidence_role: EvidenceRole = Field(alias="evidenceRole")


VerifierCandidateFinding.model_rebuild()


class VerifierResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    findings: tuple[VerifierCandidateFinding, ...] = Field(min_length=1)
    policy_version: str = Field(default=ANNOTATION_POLICY_VERSION, alias="policyVersion")


class SemanticVerifier(Protocol):
    def verify(self, *, claims: Sequence[object], source_text: str, run_id: str) -> object: ...


def provider_metadata(provider: object) -> dict[str, str | None]:
    """Read non-sensitive identity metadata exposed by an approved provider."""

    def value(*names: str, default: str | None = None) -> str | None:
        for name in names:
            item = getattr(provider, name, None)
            if item is not None:
                return str(item)
        return default

    return {
        "model_id": value("model_id", "modelId", default="configured-verifier"),
        "model_version": value("model_version", "modelVersion", default="unknown"),
        "prompt_version": value("prompt_version", "promptVersion", default="verification-v1"),
        "prompt_hash": value("prompt_hash", "promptHash", default="sha256:verification-v1"),
    }


class StructuredVerifierAdapter:
    """Invoke one pluggable provider and validate its structured response."""

    def __init__(self, provider: object, *, max_attempts: int = 2) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        self.provider = provider
        self.max_attempts = max_attempts

    def verify(self, *, claims: Sequence[object], source_text: str, run_id: str) -> VerifierResponse:
        method = (
            getattr(self.provider, "verify", None)
            or getattr(self.provider, "verify_claims", None)
            or getattr(self.provider, "complete", None)
        )
        if method is None and callable(self.provider):
            method = self.provider
        if method is None:
            raise ProviderUnavailableError("No evidence-verifier provider is configured.")

        last_error: Exception | None = None
        for _ in range(self.max_attempts):
            try:
                raw = self._call(method, claims=claims, source_text=source_text, run_id=run_id)
                response = parse_verifier_output(raw)
                if response.policy_version != ANNOTATION_POLICY_VERSION:
                    raise MalformedVerifierOutputError("Verifier output used an unsupported annotation policy version.")
                return response
            except (ProviderTimeoutError, TimeoutError) as error:
                last_error = error
            except (ProviderUnavailableError, MalformedVerifierOutputError) as error:
                last_error = error
            except ValidationError as error:
                last_error = MalformedVerifierOutputError("Verifier output failed the response schema.")
            except Exception as error:  # provider exceptions are intentionally redacted
                last_error = ProviderUnavailableError("The evidence-verifier provider failed.")
        if isinstance(last_error, VerifierError):
            raise last_error
        raise ProviderUnavailableError("The evidence-verifier provider failed.") from last_error

    @staticmethod
    def _call(method: object, *, claims: Sequence[object], source_text: str, run_id: str) -> object:
        if not callable(method):
            raise ProviderUnavailableError("The evidence-verifier provider is not callable.")
        parameters = inspect.signature(method).parameters
        kwargs: dict[str, object] = {}
        if "claims" in parameters:
            kwargs["claims"] = claims
        if "source_text" in parameters:
            kwargs["source_text"] = source_text
        elif "transcript" in parameters:
            kwargs["transcript"] = source_text
        if "run_id" in parameters:
            kwargs["run_id"] = run_id
        elif "verification_run_id" in parameters:
            kwargs["verification_run_id"] = run_id
        if kwargs:
            return method(**kwargs)
        return method(claims, source_text, run_id)


def parse_verifier_output(raw: object) -> VerifierResponse:
    if isinstance(raw, VerifierResponse):
        return raw
    if isinstance(raw, (str, bytes, bytearray)):
        try:
            raw = json.loads(raw)
        except (TypeError, json.JSONDecodeError) as error:
            raise MalformedVerifierOutputError("Verifier output was not valid JSON.") from error
    if isinstance(raw, Mapping):
        if "findings" not in raw:
            raise MalformedVerifierOutputError("Verifier output is missing findings.")
        payload: object = raw
    elif isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, bytearray)):
        payload = {"findings": list(raw)}
    else:
        raise MalformedVerifierOutputError("Verifier output must be a structured object.")
    try:
        return VerifierResponse.model_validate(payload)
    except ValidationError as error:
        raise MalformedVerifierOutputError("Verifier output failed the response schema.") from error

