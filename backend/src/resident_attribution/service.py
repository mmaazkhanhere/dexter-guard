"""Fail-closed attribution of claims to explicit synthetic resident aliases."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class AttributionFinding:
    claim_id: str
    outcome: str
    rule_code: str
    explanation: str
    evidence: tuple[tuple[int, int], ...]


class ResidentAttributionChecker:
    """Uses only aliases explicitly provided on the immutable source document.

    No name, pronoun, or sentence order is used to infer an identity.  A claim
    naming an alias mapped to a different resident is a mismatch; a pronoun or
    unmapped name in a multi-resident transcript remains uncertain.
    """

    _pronoun = re.compile(r"\b(?:sie|ihr|ihre|ihren|ihrem|ihm|er|sein|seine|seinen|seinem)\b", re.IGNORECASE)

    def check(self, *, source, claims) -> tuple[AttributionFinding, ...]:
        aliases = {alias.casefold(): resident_id for resident_id, values in source.resident_aliases.items() for alias in values}
        if not aliases:
            return ()
        source_hits = self._source_alias_spans(source.transcript_text, aliases)
        distinct_residents = {resident for resident, _ in source_hits.values()}
        findings: list[AttributionFinding] = []
        for claim in claims:
            claim_hits = self._claim_aliases(claim.claim_text, aliases)
            if claim_hits:
                residents = {aliases[hit.casefold()] for hit in claim_hits}
                if len(residents) != 1:
                    findings.append(self._uncertain(claim, source_hits, "The claim names more than one explicitly mapped resident."))
                    continue
                assigned = next(iter(residents))
                if assigned != source.resident_test_id:
                    evidence = tuple(span for resident, span in source_hits.values() if resident == assigned)
                    findings.append(AttributionFinding(claim.id, "MISMATCH", "RESIDENT-001", f"Claim explicitly names an alias mapped to {assigned}, not the selected resident {source.resident_test_id}.", evidence))
            elif len(distinct_residents) > 1 and self._pronoun.search(claim.claim_text):
                findings.append(self._uncertain(claim, source_hits, "The claim uses a pronoun while the transcript contains multiple explicitly mapped residents."))
            elif len(distinct_residents) > 1 and not claim_hits:
                findings.append(self._uncertain(claim, source_hits, "The claim has no explicit resident alias while the transcript contains multiple explicitly mapped residents."))
        return tuple(findings)

    @staticmethod
    def _source_alias_spans(text: str, aliases: dict[str, str]) -> dict[str, tuple[str, tuple[int, int]]]:
        hits: dict[str, tuple[str, tuple[int, int]]] = {}
        for alias, resident in aliases.items():
            match = re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", text, re.IGNORECASE)
            if match:
                hits[alias] = (resident, (match.start(), match.end()))
        return hits

    @staticmethod
    def _claim_aliases(text: str, aliases: dict[str, str]) -> tuple[str, ...]:
        return tuple(alias for alias in aliases if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", text, re.IGNORECASE))

    @staticmethod
    def _uncertain(claim, source_hits, explanation: str) -> AttributionFinding:
        return AttributionFinding(claim.id, "UNCERTAIN", "RESIDENT-002", explanation, tuple(span for _, span in source_hits.values()))
