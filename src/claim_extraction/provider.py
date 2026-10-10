"""Provider response parsing and provider-independent error types."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any


class ExtractionProviderError(RuntimeError):
    """Base error for failures at the untrusted provider boundary."""


class ProviderTimeoutError(ExtractionProviderError):
    pass


class ProviderUnavailableError(ExtractionProviderError):
    pass


class MalformedProviderOutputError(ExtractionProviderError):
    pass


def parse_provider_output(raw: object) -> tuple[object, ...]:
    """Decode the deliberately small provider envelope without accepting extras."""

    value: object = raw
    if isinstance(raw, (str, bytes, bytearray)):
        try:
            value = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as error:
            raise MalformedProviderOutputError("The provider returned invalid JSON.") from error

    if isinstance(value, Mapping):
        allowed = {"claims"}
        if set(value) - allowed:
            raise MalformedProviderOutputError("The provider response contains unsupported fields.")
        claims = value.get("claims")
    else:
        claims = value

    if not isinstance(claims, (list, tuple)):
        raise MalformedProviderOutputError("The provider response must contain a claims array.")
    return tuple(claims)


def provider_metadata(provider: Any) -> dict[str, str | None]:
    return {
        "provider_version": getattr(provider, "provider_version", None),
        "model_version": getattr(provider, "model_version", getattr(provider, "model_id", None)),
        "prompt_version": getattr(provider, "prompt_version", "claim-extraction-v1"),
    }
