"""Untrusted semantic-provider boundary with bounded timeout and retries."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from typing import Callable, Sequence

from claim_extraction.models import Claim

from .contracts import SemanticRelation, SourceFact
from .matching import MatchingIntegrityError, SemanticCoverageMatcher, validate_relations


class ProviderOutputError(ValueError):
    """Provider output was malformed or not closed over requested records."""


class ProviderTimeoutError(TimeoutError):
    """The semantic provider did not finish within the bounded timeout."""


class BoundedSemanticMatcher:
    """Run a provider at most twice with one stable operation identity."""

    matcher_version = "bounded-provider-v1"
    timeout_seconds = 30
    max_attempts = 2

    def __init__(self, provider: Callable[[Sequence[SourceFact], Sequence[Claim], str], Sequence[SemanticRelation]], *, timeout_seconds: int = 30) -> None:
        self.provider = provider
        self.timeout_seconds = timeout_seconds
        self.last_retry_count = 0

    def match(self, facts: Sequence[SourceFact], claims: Sequence[Claim], *, run_id: str) -> tuple[SemanticRelation, ...]:
        last_error: Exception | None = None
        self.last_retry_count = 0
        for attempt in range(self.max_attempts):
            if attempt:
                self.last_retry_count += 1
            with ThreadPoolExecutor(max_workers=1, thread_name_prefix="coverage-matcher") as executor:
                future = executor.submit(self.provider, facts, claims, run_id)
                try:
                    raw = future.result(timeout=self.timeout_seconds)
                except FutureTimeout as error:
                    future.cancel()
                    last_error = ProviderTimeoutError("semantic provider exceeded the 30-second timeout")
                    continue
                except Exception as error:  # provider failures are not UNCERTAIN coverage
                    last_error = error
                    continue
            try:
                relations = tuple(raw)
                if any(not isinstance(item, SemanticRelation) for item in relations):
                    raise ProviderOutputError("semantic provider returned a malformed relation")
                return validate_relations(relations, facts, claims)
            except (MatchingIntegrityError, TypeError, ValueError) as error:
                raise ProviderOutputError(str(error)) from error
        if isinstance(last_error, ProviderTimeoutError):
            raise last_error
        raise ProviderOutputError("semantic provider failed after two attempts") from last_error
