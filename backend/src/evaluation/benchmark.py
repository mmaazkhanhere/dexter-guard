from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone

from .contracts import (
    AnnotatedCandidateClaim, AnnotatedSourceFact, AnnotationProvenance, BenchmarkDataset, DatasetStatus,
    DatasetSplit, ErrorCategory, EvaluationCandidate, EvaluationCase, EvidenceStatus, GroundTruthError,
    SourceSnapshotReference, SourceSpan,
)


_CREATED = datetime(2026, 1, 1, tzinfo=timezone.utc)

CURATED_DATASET_ID = "synthetic-german-nursing-curated-heldout"
CURATED_DATASET_VERSION = "008-curated-v1"
CURATED_REQUIRED_TAGS = frozenset({
    "CORRECT_PARAPHRASE", "NUMERIC_MISMATCH", "NEGATION_CHANGE",
    "UNSUPPORTED_FACT", "IMPORTANT_OMISSION", "ATTRIBUTION_CHANGE",
})


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _span(source_id: str, text: str, needle: str) -> SourceSpan:
    start = text.index(needle)
    return SourceSpan(sourceId=source_id, sourceVersion=1, start=start, end=start + len(needle))


def _case(index: int) -> EvaluationCase:
    categories = (
        ("SUPPORTED", None, "Die Bewohnerin berichtet über guten Schlaf.", "Schlaf war gut.", EvidenceStatus.SUPPORTED, "FAITHFULLY_COVERED"),
        ("UNSUPPORTED_FACT", ErrorCategory.UNSUPPORTED_FACT, "Die Bewohnerin berichtet keinen Schwindel.", "Schwindel vorhanden.", EvidenceStatus.UNSUPPORTED, "FAITHFULLY_COVERED"),
        ("EXPLICIT_CONTRADICTION", ErrorCategory.EXPLICIT_CONTRADICTION, "Die Bewohnerin verneint Schmerzen.", "Schmerzen vorhanden.", EvidenceStatus.CONTRADICTED, "FAITHFULLY_COVERED"),
        ("NUMERIC_MISMATCH", ErrorCategory.NUMERIC_MISMATCH, "Die Temperatur beträgt 37,2 Grad Celsius.", "Die Temperatur beträgt 38,2 Grad Celsius.", EvidenceStatus.CONTRADICTED, "FAITHFULLY_COVERED"),
        ("UNIT_MISMATCH", ErrorCategory.UNIT_MISMATCH, "Die Trinkmenge beträgt 500 ml.", "Die Trinkmenge beträgt 500 l.", EvidenceStatus.CONTRADICTED, "FAITHFULLY_COVERED"),
        ("NEGATION_CHANGE", ErrorCategory.NEGATION_CHANGE, "Die Bewohnerin hat keinen Husten.", "Die Bewohnerin hat Husten.", EvidenceStatus.CONTRADICTED, "FAITHFULLY_COVERED"),
        ("CERTAINTY_CHANGE", ErrorCategory.CERTAINTY_CHANGE, "Möglicherweise ist die Bewohnerin müde.", "Die Bewohnerin ist müde.", EvidenceStatus.UNCERTAIN, "FAITHFULLY_COVERED"),
        ("ATTRIBUTION_CHANGE", ErrorCategory.ATTRIBUTION_CHANGE, "Die Bewohnerin berichtet über Übelkeit.", "Die Pflegekraft berichtet über Übelkeit.", EvidenceStatus.CONTRADICTED, "FAITHFULLY_COVERED"),
        ("CLINICAL_INFERENCE", ErrorCategory.CLINICAL_INFERENCE, "Die Bewohnerin wirkt blass.", "Die Bewohnerin hat eine Anämie.", EvidenceStatus.UNSUPPORTED, "FAITHFULLY_COVERED"),
        ("IMPORTANT_OMISSION", ErrorCategory.IMPORTANT_OMISSION, "Die Bewohnerin trank 300 ml Wasser.", "Die Bewohnerin war wach und ansprechbar.", EvidenceStatus.SUPPORTED, "OMITTED"),
        ("AMBIGUOUS_SOURCE", None, "Die Bewohnerin berichtet eventuell über Schwindel.", "Eventuell Schwindel berichtet.", EvidenceStatus.UNCERTAIN, "FAITHFULLY_COVERED"),
        ("HARMLESS_PARAPHRASE", None, "Die Bewohnerin ging mit Unterstützung zum Tisch.", "Die Bewohnerin wurde unterstützt zum Tisch begleitet.", EvidenceStatus.SUPPORTED, "FAITHFULLY_COVERED"),
    )
    tag, category, source_text, note_body, expected_status, coverage = categories[index % len(categories)]
    source_text = f"{source_text} Fall {index}."
    note_body = f"{note_body} Fall {index}."
    source_id = f"synthetic-source-{index:03d}"
    candidate_id = f"candidate-{index:03d}"
    scenario_id = f"scenario-{index:03d}"
    claim_id = f"claim-{index:03d}"
    source_hash = _sha(source_text)
    note_hash = _sha(note_body)
    source_ref = SourceSnapshotReference(
        sourceId=source_id, sourceVersion=1, sourceTextHash=source_hash,
        residentTestId=f"synthetic-resident-{index:03d}", language="de-DE",
        transcriptLocator=f"data/evaluation/008-v1/{scenario_id}/source.txt", transcriptText=source_text,
    )
    source_span = _span(source_id, source_text, source_text.split(".")[0] + ".")
    fact = AnnotatedSourceFact(
        sourceFactId=f"fact-{index:03d}", sourceSpans=(source_span,), expectation="IMPORTANT",
        applicableToCandidateIds="ALL", expectedEvidenceRelationship="DIRECT_SOURCE_SUPPORT",
        expectedCoverage=coverage,
    )
    claim_span = note_body
    claim = AnnotatedCandidateClaim(
        annotatedClaimId=f"annotated-{claim_id}", claimId=claim_id, statementReference=claim_span,
        expectedPrimaryStatus=expected_status, expectedDiscrepancies=((category.value if category else ""),) if category else (),
        expectedEvidenceSpans=(source_span,), scorable=True,
    )
    errors: tuple[GroundTruthError, ...] = ()
    claims: tuple[AnnotatedCandidateClaim, ...] = (claim,)
    if category is ErrorCategory.IMPORTANT_OMISSION:
        claims = ()
        errors = (GroundTruthError(
            errorId=f"error-{index:03d}", candidateId=candidate_id, affectedAnnotatedClaimId=None,
            affectedSourceFactId=fact.source_fact_id, category=category, severity="CRITICAL",
            expectedPrimaryStatus=None, requiredDiscrepancyOrRule="MISSING_EXPECTED_SOURCE_FACT",
            sourceEvidenceSpans=(source_span,), applicable=True,
        ),)
    elif category is not None:
        errors = (GroundTruthError(
            errorId=f"error-{index:03d}", candidateId=candidate_id, affectedAnnotatedClaimId=claim.annotated_claim_id,
            affectedSourceFactId=None, category=category, severity="CRITICAL" if index % 3 == 0 else "MAJOR",
            expectedPrimaryStatus=expected_status, requiredDiscrepancyOrRule=category.value,
            conflictingAttribute="semantic_attribute" if category in {ErrorCategory.NUMERIC_MISMATCH, ErrorCategory.UNIT_MISMATCH, ErrorCategory.NEGATION_CHANGE, ErrorCategory.CERTAINTY_CHANGE, ErrorCategory.ATTRIBUTION_CHANGE} else None,
            expectedValue=None, sourceEvidenceSpans=(source_span,), applicable=True,
        ),)
    if index % 25 == 0:
        second = GroundTruthError(
            errorId=f"error-{index:03d}-b", candidateId=candidate_id, affectedAnnotatedClaimId=claim.annotated_claim_id,
            affectedSourceFactId=None, category=ErrorCategory.OTHER, severity="MINOR",
            expectedPrimaryStatus=expected_status, requiredDiscrepancyOrRule="SECONDARY_DISCREPANCY",
            sourceEvidenceSpans=(source_span,), applicable=True,
        )
        errors = (*errors, second)
    split = DatasetSplit.DEVELOPMENT if index < 60 else DatasetSplit.VALIDATION if index < 80 else DatasetSplit.HELD_OUT
    tags = (tag, "MULTIPLE_ERRORS" if len(errors) > 1 else "SINGLE_ERROR", "FAMILY_UNIQUE")
    if tag in {"AMBIGUOUS_SOURCE", "HARMLESS_PARAPHRASE"}:
        tags = (*tags, tag)
    return EvaluationCase(
        scenarioId=scenario_id, scenarioFamilyId=f"family-{index:03d}", datasetVersion="008-v1", split=split,
        tags=tags, source=source_ref, referenceFacts=(fact,),
        candidateNotes=(EvaluationCandidate(
            candidateId=candidate_id, noteId=f"note-{index:03d}", noteRevision=1, noteBodyHash=note_hash,
            noteBody=note_body, origin="FIXTURE", annotatedClaims=claims, errorInstances=errors,
        ),),
        annotationProvenance=AnnotationProvenance(
            annotatorLabel="synthetic-benchmark-team", annotatedAt=_CREATED,
            reviewStatus="INDEPENDENTLY_REVIEWED", guideVersion="EVIDENCE_ANNOTATION-v1",
            rationaleLocator=f"data/evaluation/008-v1/{scenario_id}/annotation.json",
        ),
    )


def default_dataset() -> BenchmarkDataset:
    scenarios = tuple(_case(index) for index in range(100))
    draft = BenchmarkDataset(
        datasetId="synthetic-german-nursing-008", datasetVersion="008-v1", contentHash="0" * 64,
        status=DatasetStatus.ACCEPTED, language="de-DE", scenarioCount=len(scenarios),
        annotationGuideVersion="EVIDENCE_ANNOTATION-v1", evidenceStatusPolicyVersion="EVIDENCE_STATUS-v1",
        annotationPolicyVersion="EVIDENCE_ANNOTATION-v1", matchingPolicyVersion="EVALUATION_MATCHING-v1",
        createdAt=_CREATED, acceptedAt=_CREATED, scenarios=scenarios,
    )
    return draft.model_copy(update={"content_hash": _sha(draft.canonical_content())})


@dataclass(frozen=True)
class _CuratedScenario:
    """Manual synthetic annotation inputs for the separate held-out corpus."""

    scenario_id: str
    source_text: str
    note_body: str
    evidence_text: str
    expected_status: EvidenceStatus | None
    category: ErrorCategory | None


_CURATED_SCENARIOS: tuple[_CuratedScenario, ...] = (
    _CuratedScenario("paraphrase-fruehstueck", "Beim Frühstück saß die Bewohnerin aufrecht im Sessel. Sie aß etwa die Hälfte des Brotes und trank eine Tasse Tee. Anschließend bat sie um eine Pause.", "Beim Frühstück nahm die Bewohnerin ungefähr die Hälfte der Mahlzeit und eine Tasse Tee zu sich.", "Sie aß etwa die Hälfte des Brotes und trank eine Tasse Tee.", EvidenceStatus.SUPPORTED, None),
    _CuratedScenario("paraphrase-transfer", "Am Vormittag wurde der Bewohner vom Bett in den Rollstuhl umgesetzt. Dabei benötigte er eine Person zur Sicherung. Danach fuhr er selbstständig zum Fenster.", "Der Transfer vom Bett in den Rollstuhl gelang mit Sicherung durch eine Pflegeperson.", "Dabei benötigte er eine Person zur Sicherung.", EvidenceStatus.SUPPORTED, None),
    _CuratedScenario("paraphrase-nachtschlaf", "In der Nacht klingelte die Bewohnerin einmal wegen Durst. Nach einem Glas Wasser schlief sie bis 05:30 Uhr weiter. Morgens wirkte sie ausgeschlafen.", "Nach einmaligem Aufwachen wegen Durst setzte die Bewohnerin ihren Schlaf bis 05:30 Uhr fort.", "Nach einem Glas Wasser schlief sie bis 05:30 Uhr weiter.", EvidenceStatus.SUPPORTED, None),
    _CuratedScenario("paraphrase-hautpflege", "Bei der Morgenpflege war die Haut an den Fersen intakt und trocken. Die Bewohnerin wünschte eine rückfettende Lotion. Diese wurde dünn aufgetragen.", "Die trockene, intakte Haut an den Fersen wurde mit Lotion gepflegt.", "Bei der Morgenpflege war die Haut an den Fersen intakt und trocken.", EvidenceStatus.SUPPORTED, None),
    _CuratedScenario("paraphrase-orientierung", "Nach dem Mittagessen fragte der Bewohner nach dem Wochentag. Nach der Erinnerung nannte er Dienstag richtig. Im Gespräch blieb er ruhig und zugewandt.", "Nach einer Erinnerung konnte der Bewohner den Wochentag korrekt benennen.", "Nach der Erinnerung nannte er Dienstag richtig.", EvidenceStatus.SUPPORTED, None),
    _CuratedScenario("paraphrase-schmerz", "Vor der Mobilisation bewertete die Bewohnerin ihre Knieschmerzen mit drei von zehn. Nach einer kurzen Ruhepause wollte sie trotzdem zum Speiseraum gehen. Der Gang erfolgte mit Rollator.", "Trotz leichter Knieschmerzen mobilisierte sich die Bewohnerin mit dem Rollator zum Speiseraum.", "Der Gang erfolgte mit Rollator.", EvidenceStatus.SUPPORTED, None),
    _CuratedScenario("numeric-temperatur", "Um 14:00 Uhr betrug die Temperatur des Bewohners 37,4 Grad Celsius. Er trank danach Wasser. Schüttelfrost wurde nicht beobachtet.", "Die Temperatur betrug 38,4 Grad Celsius.", "Um 14:00 Uhr betrug die Temperatur des Bewohners 37,4 Grad Celsius.", EvidenceStatus.CONTRADICTED, ErrorCategory.NUMERIC_MISMATCH),
    _CuratedScenario("numeric-trinkmenge", "Bis zum frühen Nachmittag hatte die Bewohnerin 650 ml Tee und Wasser getrunken. Zum Abendessen stellte die Pflege zusätzlich ein Getränk bereit. Die Schleimhäute wirkten feucht.", "Die Trinkmenge bis zum Nachmittag lag bei 950 ml.", "Bis zum frühen Nachmittag hatte die Bewohnerin 650 ml Tee und Wasser getrunken.", EvidenceStatus.CONTRADICTED, ErrorCategory.NUMERIC_MISMATCH),
    _CuratedScenario("numeric-blutdruck", "Vor der Abendmedikation wurde ein Blutdruck von 128 zu 76 mmHg gemessen. Der Bewohner verneinte Beschwerden. Die Messung wurde im Sitz wiederholt.", "Der Blutdruck lag bei 168 zu 96 mmHg.", "Vor der Abendmedikation wurde ein Blutdruck von 128 zu 76 mmHg gemessen.", EvidenceStatus.CONTRADICTED, ErrorCategory.NUMERIC_MISMATCH),
    _CuratedScenario("numeric-gewicht", "Beim wöchentlichen Wiegen zeigte die Waage 68,2 kg. Der Bewohner trug dabei Hausschuhe und einen Pullover. Der Wert wurde im Verlaufsbogen notiert.", "Das Gewicht betrug 72,8 kg.", "Beim wöchentlichen Wiegen zeigte die Waage 68,2 kg.", EvidenceStatus.CONTRADICTED, ErrorCategory.NUMERIC_MISMATCH),
    _CuratedScenario("numeric-spaziergang", "Am Nachmittag ging die Bewohnerin mit Begleitung einmal den Flur entlang. Die dokumentierte Strecke betrug ungefähr 35 Meter. Danach setzte sie sich für zehn Minuten hin.", "Die Bewohnerin ging etwa 135 Meter auf dem Flur.", "Die dokumentierte Strecke betrug ungefähr 35 Meter.", EvidenceStatus.CONTRADICTED, ErrorCategory.NUMERIC_MISMATCH),
    _CuratedScenario("numeric-ausscheidung", "Im Messbecher befanden sich am Morgen 280 ml Urin. Die Farbe war hellgelb. Die Bewohnerin äußerte keinen Harndrang.", "Die Urinmenge am Morgen betrug 480 ml.", "Im Messbecher befanden sich am Morgen 280 ml Urin.", EvidenceStatus.CONTRADICTED, ErrorCategory.NUMERIC_MISMATCH),
    _CuratedScenario("negation-schwindel", "Beim Aufstehen fragte die Pflegekraft nach Schwindel. Die Bewohnerin verneinte Schwindel und hielt sich am Bettgestell fest. Der weitere Transfer verlief langsam.", "Die Bewohnerin berichtete beim Aufstehen über Schwindel.", "verneinte Schwindel", EvidenceStatus.CONTRADICTED, ErrorCategory.NEGATION_CHANGE),
    _CuratedScenario("negation-uebelkeit", "Vor dem Mittagessen sagte der Bewohner, ihm sei nicht übel. Er aß anschließend eine kleine Portion Suppe. Nach dem Essen blieb er im Gemeinschaftsraum.", "Vor dem Mittagessen bestand Übelkeit.", "Vor dem Mittagessen sagte der Bewohner, ihm sei nicht übel.", EvidenceStatus.CONTRADICTED, ErrorCategory.NEGATION_CHANGE),
    _CuratedScenario("negation-schmerz", "Bei der Lagerung fragte die Pflege nach Schmerzen im Rücken. Die Bewohnerin antwortete, sie habe keine Schmerzen. Sie wünschte nur ein zusätzliches Kissen.", "Bei der Lagerung hatte die Bewohnerin Rückenschmerzen.", "Die Bewohnerin antwortete, sie habe keine Schmerzen.", EvidenceStatus.CONTRADICTED, ErrorCategory.NEGATION_CHANGE),
    _CuratedScenario("negation-husten", "Während der Morgenrunde hustete der Bewohner nicht. Seine Stimme war klar. Er trank danach warmen Tee.", "Während der Morgenrunde zeigte der Bewohner Husten.", "Während der Morgenrunde hustete der Bewohner nicht.", EvidenceStatus.CONTRADICTED, ErrorCategory.NEGATION_CHANGE),
    _CuratedScenario("negation-roetung", "Beim Wechseln der Strümpfe zeigte sich an beiden Unterschenkeln keine Rötung. Die Haut war warm und trocken. Anschließend wurden die Beine eingecremt.", "An den Unterschenkeln war eine Rötung sichtbar.", "zeigte sich an beiden Unterschenkeln keine Rötung.", EvidenceStatus.CONTRADICTED, ErrorCategory.NEGATION_CHANGE),
    _CuratedScenario("negation-unruhe", "In der Spätschicht lief im Zimmer leise Radio. Der Bewohner war nicht unruhig und las in einer Zeitschrift. Er bat um das Ausschalten des Lichts um 21 Uhr.", "Der Bewohner war in der Spätschicht unruhig.", "war nicht unruhig", EvidenceStatus.CONTRADICTED, ErrorCategory.NEGATION_CHANGE),
    _CuratedScenario("unsupported-diagnose", "Die Bewohnerin wirkte am Morgen blass und bevorzugte den Sessel. Sie trank ein Glas Wasser. Eine ärztliche Diagnose oder Untersuchung wird im Bericht nicht genannt.", "Bei der Bewohnerin liegt eine Lungenentzündung vor.", "Die Bewohnerin wirkte am Morgen blass und bevorzugte den Sessel.", EvidenceStatus.UNSUPPORTED, ErrorCategory.UNSUPPORTED_FACT),
    _CuratedScenario("unsupported-medikament", "Der Bewohner schlief nach dem Abendessen im Sessel ein. Die Pflege weckte ihn zum Zähneputzen. Eine Medikamentengabe wird im Bericht nicht beschrieben.", "Der Bewohner erhielt ein Schlafmittel.", "Eine Medikamentengabe wird im Bericht nicht beschrieben.", EvidenceStatus.UNSUPPORTED, ErrorCategory.UNSUPPORTED_FACT),
    _CuratedScenario("unsupported-besuch", "Die Tochter rief am Vormittag an und erkundigte sich nach dem Befinden. Die Bewohnerin sprach danach kurz über das Telefonat. Ein Besuch im Haus fand nicht statt.", "Die Tochter besuchte die Bewohnerin am Vormittag.", "Ein Besuch im Haus fand nicht statt.", EvidenceStatus.UNSUPPORTED, ErrorCategory.UNSUPPORTED_FACT),
    _CuratedScenario("unsupported-sturz", "Der Bewohner saß nachmittags im Aufenthaltsraum und spielte Karten. Beim Aufstehen nutzte er seinen Rollator. Ein Sturzereignis wird nicht berichtet.", "Der Bewohner ist am Nachmittag gestürzt.", "Ein Sturzereignis wird nicht berichtet.", EvidenceStatus.UNSUPPORTED, ErrorCategory.UNSUPPORTED_FACT),
    _CuratedScenario("unsupported-allergie", "Zum Mittag erhielt die Bewohnerin Kartoffelsuppe und Brot. Sie äußerte, die Suppe schmecke ihr. Angaben zu Allergien enthält der Bericht nicht.", "Die Bewohnerin hat eine Penicillinallergie.", "Angaben zu Allergien enthält der Bericht nicht.", EvidenceStatus.UNSUPPORTED, ErrorCategory.UNSUPPORTED_FACT),
    _CuratedScenario("unsupported-wundversorgung", "Am rechten Unterarm befand sich ein kleiner blauer Fleck. Die Bewohnerin sagte, dieser sei nicht schmerzhaft. Ein Verband oder eine Wundversorgung wird nicht erwähnt.", "Am rechten Unterarm wurde ein neuer Verband angelegt.", "Ein Verband oder eine Wundversorgung wird nicht erwähnt.", EvidenceStatus.UNSUPPORTED, ErrorCategory.UNSUPPORTED_FACT),
    _CuratedScenario("omission-abfuehrmittel", "Nach zwei Tagen ohne Stuhlgang erhielt der Bewohner morgens ein verordnetes Abführmittel. Er trank dazu ein Glas Wasser. Am Nachmittag wurde das Befinden erneut erfragt.", "Der Bewohner trank morgens ein Glas Wasser und wurde am Nachmittag nach seinem Befinden gefragt.", "erhielt der Bewohner morgens ein verordnetes Abführmittel.", None, ErrorCategory.IMPORTANT_OMISSION),
    _CuratedScenario("omission-sturzprophylaxe", "Vor dem Schlafengehen erinnerte die Pflege die Bewohnerin an die Klingel. Die Bremsen am Rollstuhl wurden festgestellt. Danach wurde ein Nachtlicht eingeschaltet.", "Vor dem Schlafengehen wurde ein Nachtlicht eingeschaltet.", "Die Bremsen am Rollstuhl wurden festgestellt.", None, ErrorCategory.IMPORTANT_OMISSION),
    _CuratedScenario("omission-trinkangebot", "Am heißen Nachmittag bot die Pflege dem Bewohner dreimal Wasser an. Er trank insgesamt zwei kleine Gläser. Die Fensterläden blieben geschlossen.", "Die Fensterläden blieben am heißen Nachmittag geschlossen.", "bot die Pflege dem Bewohner dreimal Wasser an.", None, ErrorCategory.IMPORTANT_OMISSION),
    _CuratedScenario("attribution-schwindel", "Die Bewohnerin sagte beim Waschen, ihr sei kurz schwindelig gewesen. Die Pflege beobachtete dabei einen sicheren Stand. Nach einer Pause wollte die Bewohnerin weiterwaschen.", "Die Pflegekraft beobachtete Schwindel bei der Bewohnerin.", "Die Bewohnerin sagte beim Waschen, ihr sei kurz schwindelig gewesen.", EvidenceStatus.CONTRADICTED, ErrorCategory.ATTRIBUTION_CHANGE),
    _CuratedScenario("attribution-telefonat", "Der Sohn berichtete am Telefon, dass seine Mutter am Wochenende gut geschlafen habe. Die Bewohnerin selbst sprach an diesem Morgen nicht über ihren Schlaf. Sie lächelte beim Gespräch über den Anruf.", "Die Bewohnerin berichtete, am Wochenende gut geschlafen zu haben.", "Der Sohn berichtete am Telefon, dass seine Mutter am Wochenende gut geschlafen habe.", EvidenceStatus.CONTRADICTED, ErrorCategory.ATTRIBUTION_CHANGE),
    _CuratedScenario("attribution-hilfe", "Beim Anziehen bot die Pflege dem Bewohner Hilfe mit den Schuhen an. Er lehnte ab und schloss die Klettverschlüsse selbst. Danach ging er zum Frühstück.", "Der Bewohner bat beim Anziehen um Hilfe mit den Schuhen.", "bot die Pflege dem Bewohner Hilfe mit den Schuhen an.", EvidenceStatus.CONTRADICTED, ErrorCategory.ATTRIBUTION_CHANGE),
)


def curated_held_out_dataset() -> BenchmarkDataset:
    """Return the 30-case, varied synthetic corpus for actual-verifier evaluation.

    It deliberately contains no development or validation split and is labelled
    ``PENDING`` until an independent annotation review is actually recorded.
    """
    cases: list[EvaluationCase] = []
    for index, item in enumerate(_CURATED_SCENARIOS, start=1):
        source_id = f"curated-source-{index:03d}"
        candidate_id = f"curated-candidate-{index:03d}"
        evidence_span = _span(source_id, item.source_text, item.evidence_text)
        source = SourceSnapshotReference(
            sourceId=source_id, sourceVersion=1, sourceTextHash=_sha(item.source_text),
            residentTestId=f"synthetic-curated-resident-{index:03d}", language="de-DE",
            transcriptLocator=f"data/evaluation/{CURATED_DATASET_VERSION}/{item.scenario_id}/source.txt",
            transcriptText=item.source_text,
        )
        fact = AnnotatedSourceFact(
            sourceFactId=f"curated-fact-{index:03d}", sourceSpans=(evidence_span,), expectation="IMPORTANT",
            applicableToCandidateIds="ALL", expectedEvidenceRelationship="DIRECT_SOURCE_SUPPORT",
            expectedCoverage="OMITTED" if item.category is ErrorCategory.IMPORTANT_OMISSION else "FAITHFULLY_COVERED",
        )
        claims: tuple[AnnotatedCandidateClaim, ...] = ()
        errors: tuple[GroundTruthError, ...] = ()
        if item.expected_status is not None:
            claim = AnnotatedCandidateClaim(
                annotatedClaimId=f"curated-claim-{index:03d}", claimId=f"curated-runtime-claim-{index:03d}",
                statementReference=item.note_body, expectedPrimaryStatus=item.expected_status,
                expectedDiscrepancies=(item.category.value,) if item.category else (),
                expectedEvidenceSpans=(evidence_span,), scorable=True,
            )
            claims = (claim,)
            if item.category is not None:
                errors = (GroundTruthError(
                    errorId=f"curated-error-{index:03d}", candidateId=candidate_id,
                    affectedAnnotatedClaimId=claim.annotated_claim_id, affectedSourceFactId=None,
                    category=item.category, severity="CRITICAL", expectedPrimaryStatus=item.expected_status,
                    requiredDiscrepancyOrRule=item.category.value, sourceEvidenceSpans=(evidence_span,),
                    applicable=True,
                ),)
        else:
            errors = (GroundTruthError(
                errorId=f"curated-error-{index:03d}", candidateId=candidate_id,
                affectedAnnotatedClaimId=None, affectedSourceFactId=fact.source_fact_id,
                category=ErrorCategory.IMPORTANT_OMISSION, severity="CRITICAL", expectedPrimaryStatus=None,
                requiredDiscrepancyOrRule="MISSING_EXPECTED_SOURCE_FACT", sourceEvidenceSpans=(evidence_span,),
                applicable=True,
            ),)
        tag = "CORRECT_PARAPHRASE" if item.category is None else item.category.value
        cases.append(EvaluationCase(
            scenarioId=f"curated-{item.scenario_id}", scenarioFamilyId=f"curated-family-{item.scenario_id}",
            datasetVersion=CURATED_DATASET_VERSION, split=DatasetSplit.HELD_OUT,
            tags=(tag, "CURATED_MANUAL_REVIEW"), source=source, referenceFacts=(fact,),
            candidateNotes=(EvaluationCandidate(
                candidateId=candidate_id, noteId=f"curated-note-{index:03d}", noteRevision=1,
                noteBodyHash=_sha(item.note_body), noteBody=item.note_body, origin="FIXTURE",
                annotatedClaims=claims, errorInstances=errors,
            ),),
            annotationProvenance=AnnotationProvenance(
                annotatorLabel="synthetic-curated-authoring", annotatedAt=_CREATED, reviewStatus="PENDING",
                guideVersion="EVIDENCE_ANNOTATION-v1", rationaleLocator=f"data/evaluation/{CURATED_DATASET_VERSION}/{item.scenario_id}/annotation.json",
            ),
        ))
    draft = BenchmarkDataset(
        datasetId=CURATED_DATASET_ID, datasetVersion=CURATED_DATASET_VERSION, contentHash="0" * 64,
        status=DatasetStatus.ACCEPTED, language="de-DE", scenarioCount=len(cases),
        annotationGuideVersion="EVIDENCE_ANNOTATION-v1", evidenceStatusPolicyVersion="EVIDENCE_STATUS-v1",
        annotationPolicyVersion="EVIDENCE_ANNOTATION-v1", matchingPolicyVersion="EVALUATION_MATCHING-v1",
        createdAt=_CREATED, acceptedAt=_CREATED, scenarios=tuple(cases),
    )
    return draft.model_copy(update={"content_hash": _sha(draft.canonical_content())})

