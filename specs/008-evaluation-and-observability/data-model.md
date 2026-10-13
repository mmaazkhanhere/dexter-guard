# Spec 008 Data Model and Scoring Contract

**Contract version:** `EVALUATION-CONTRACT-v1`  
**Matching policy:** `EVALUATION_MATCHING-v1`  
**Metric policy:** `EVALUATION_METRICS-v1`

This is a normative design contract. Field names may use the project’s Pydantic aliases at an HTTP boundary, but source, note, claim, finding, and review identities retain their owning-spec semantics.

## Enumerations

```text
DatasetSplit = DEVELOPMENT | VALIDATION | HELD_OUT
DatasetStatus = DRAFT | ACCEPTED | REJECTED | RETIRED
RunStatus = QUEUED | RUNNING | SUCCEEDED | PARTIALLY_FAILED | FAILED | INTERRUPTED | INVALID_DATASET
CaseStatus = PENDING | SUCCEEDED | FAILED | INVALID_OUTPUT | UNSCORABLE | SKIPPED
ResultOrigin = HISTORICAL_SAVED_RESULT | NEWLY_EXECUTED
EvidenceStatus = SUPPORTED | UNSUPPORTED | CONTRADICTED | UNCERTAIN
ErrorCategory = UNSUPPORTED_FACT | EXPLICIT_CONTRADICTION | NUMERIC_MISMATCH |
                UNIT_MISMATCH | NEGATION_CHANGE | CERTAINTY_CHANGE |
                ATTRIBUTION_CHANGE | RESIDENT_CONTEXT_MISMATCH | CLINICAL_INFERENCE |
                IMPORTANT_OMISSION | OTHER
Severity = CRITICAL | MAJOR | MINOR
MatchDisposition = MATCHED | DUPLICATE | UNMATCHED_WARNING | TARGET_LINKED_MISCLASSIFICATION |
                   FALSE_NEGATIVE | UNSCORABLE | NOT_APPLICABLE
MetricState = SCORED | NOT_APPLICABLE | UNAVAILABLE | INCOMPLETE
ComparisonStatus = VALID | INVALID_PAIR | NOT_RUN | SIMULATED
ReviewDataKind = OBSERVED | SIMULATED | UNAVAILABLE
```

`Severity` is the approved fixture severity/Spec 007 policy result; Spec 008 never assigns clinical severity. `ErrorCategory` records the error taxonomy, while producer-specific discrepancy/rule/policy values remain preserved.

## Dataset records

```text
BenchmarkDataset {
  datasetId: string
  datasetVersion: string
  contentHash: SHA-256
  status: DatasetStatus
  language: "de-DE"
  scenarioCount: integer >= 100 when ACCEPTED
  annotationGuideVersion: string
  evidenceStatusPolicyVersion: "EVIDENCE_STATUS-v1"
  annotationPolicyVersion: "EVIDENCE_ANNOTATION-v1"
  matchingPolicyVersion: "EVALUATION_MATCHING-v1"
  createdAt, acceptedAt: timezone-aware timestamp
  scenarios: EvaluationCase[100..n]
}

EvaluationCase {
  scenarioId: string
  scenarioFamilyId: string
  datasetVersion: string
  split: DatasetSplit
  tags: string[1..n]
  source: SourceSnapshotReference
  referenceFacts: AnnotatedSourceFact[]
  candidateNotes: EvaluationCandidate[1..n]
  annotationProvenance: AnnotationProvenance
}

SourceSnapshotReference {
  sourceId: string
  sourceVersion: positive integer
  sourceTextHash: SHA-256
  residentTestId: synthetic identifier
  language: "de-DE"
  transcriptLocator: immutable fixture/repository locator
}

AnnotatedSourceFact {
  sourceFactId: string
  sourceSpans: SourceSpan[1..n]
  expectation: REQUIRED | IMPORTANT | CONTEXTUAL
  applicableToCandidateIds: string[] | "ALL"
  expectedEvidenceRelationship: string
  expectedCoverage: FAITHFULLY_COVERED | OMITTED | NOT_APPLICABLE
}

EvaluationCandidate {
  candidateId: string
  noteId: string
  noteRevision: positive integer
  noteBodyHash: SHA-256
  origin: GENERATED | EXTERNALLY_SUPPLIED | FIXTURE
  annotatedClaims: AnnotatedCandidateClaim[]
  errorInstances: GroundTruthError[]
}

AnnotatedCandidateClaim {
  annotatedClaimId: string
  claimId: string | null
  statementReference: immutable note span/reference
  expectedPrimaryStatus: EvidenceStatus
  expectedDiscrepancies: string[]
  expectedEvidenceSpans: SourceSpan[]
  scorable: boolean
}

GroundTruthError {
  errorId: string
  candidateId: string
  affectedAnnotatedClaimId: string | null
  affectedSourceFactId: string | null
  category: ErrorCategory
  severity: Severity
  expectedPrimaryStatus: EvidenceStatus | null
  requiredDiscrepancyOrRule: string | null
  conflictingAttribute: string | null
  expectedValue: string | null
  sourceEvidenceSpans: SourceSpan[]
  applicable: boolean
}
```

Exactly one affected target is required for an error: `affectedAnnotatedClaimId` for claim errors or `affectedSourceFactId` for omissions. `CONTEXTUAL` facts and `applicable=false` facts never enter completeness denominators. All source spans resolve to the `SourceSnapshotReference` under zero-based Unicode-code-point, start-inclusive/end-exclusive semantics.

`AnnotationProvenance` records synthetic annotator/project label, annotation timestamp, review status, guide version, disagreements, resolution identifier, and rationale locator. It contains no real-person or healthcare information.

## Run and result records

```text
EvaluationRun {
  evaluationRunId: string
  origin: ResultOrigin
  status: RunStatus
  datasetId, datasetVersion, datasetHash: string
  selectedSplit: DatasetSplit
  selectionDigest: SHA-256
  configuration: EvaluationConfiguration
  startedAt, completedAt: timezone-aware timestamp | null
  caseResults: EvaluationCaseResult[]
  aggregateMetrics: MetricResult[]
  comparison: PairedComparisonResult | null
  failureSummary: FailureSummary
  reportSchemaVersion: "EVALUATION_REPORT-v1"
}

EvaluationConfiguration {
  codeVersion: commit/revision identifier
  environmentId: non-secret runtime identity
  modelProvider, modelId, modelVersion: string | null
  promptVersionsAndHashes: VersionedValue[]
  inferenceParameters: redacted structured values
  ruleVersionsAndRulesetVersions: VersionedValue[]
  upstreamContractVersions: VersionedValue[]
  fixtureMode: LIVE | SAVED_FIXTURE | MOCKED_PROVIDER
  pricingAssumptionsVersion: string | null
  matchingPolicyVersion: "EVALUATION_MATCHING-v1"
  randomSeed: integer | null
}

EvaluationCaseResult {
  caseExecutionId: string
  scenarioId, candidateId: string
  sourceId: string
  sourceVersion: positive integer
  sourceTextHash: SHA-256
  noteId: string
  noteRevision: positive integer
  noteBodyHash: SHA-256
  status: CaseStatus
  stageRuns: StageRunReference[]
  observedFindings: ObservedFinding[]
  matchResults: GroundTruthMatch[]
  completenessResults: SourceFactScore[]
  reviewOutcome: ReviewOutcome | null
  latency: LatencyBreakdown
  usageAndCost: UsageAndCost
  failure: EvaluationFailure | null
}

ObservedFinding {
  findingKey: string
  producer: SPEC_004 | SPEC_005 | SPEC_006 | REVIEW_OPERATIONAL
  upstreamRunId: string
  affectedClaimId: string | null
  affectedSourceFactId: string | null
  primaryStatusOrOutcome: string
  discrepancyOrRule: string | null
  conflictingAttributeOrValue: string | null
  sourceSpans: SourceSpan[]
  requiresCorrectionOrReview: boolean
}

GroundTruthMatch {
  errorId: string
  findingKey: string | null
  disposition: MatchDisposition
  reasonCode: string
  specificityScore: integer | null
}
```

`EvaluationRun` is append-only after terminal state. `SUCCEEDED` means all selected cases are terminal and no case failed or was unscorable; `PARTIALLY_FAILED` means aggregation completed with one or more failed/unscorable cases; `FAILED`, `INTERRUPTED`, and `INVALID_DATASET` retain available case/failure records but cannot be presented as passing benchmark outcomes. A stored example references the original immutable `EvaluationRun`; it does not clone it as a fresh run.

## Metric and comparison records

```text
MetricResult {
  metricId: string
  state: MetricState
  numerator: integer
  denominator: integer
  value: decimal | null
  confidenceInterval: { method, level, lower, upper } | null
  scorableCount, unscorableCount, failedCount: integer
  reason: string | null
  policyVersion: "EVALUATION_METRICS-v1"
}

PairedComparisonResult {
  comparisonId: string
  status: ComparisonStatus
  baselineRunId, validatedRunId: string
  pairResults: PairedCandidateResult[]
  reviewDataKind: ReviewDataKind
  simulationPolicyVersion: string | null
  aggregateDeltas: MetricDelta[]
}

PairedCandidateResult {
  scenarioId, candidateId: string
  candidateBodyHash: SHA-256
  baselineCaseExecutionId, validatedCaseExecutionId: string
  status: VALID | INVALID_PAIR
  invalidReason: string | null
}
```

`MetricResult` uses raw counts; `value` is derived only when `denominator > 0`. Final-note quality is retained as two raw counts—remaining factual errors and remaining omissions—plus final scorable-note count; it must not become a single rate without separately approved formula.

## Matching invariants

1. A match requires equal affected claim ID or source-fact ID, compatible category/producer, expected primary status when defined, required discrepancy/rule when defined, and expected evidence correspondence when spans are required.
2. An exact source-span match uses same immutable source ID/version and identical coordinates. A documented span-overlap equivalence may be used only for an annotation-defined larger evidence span; it must preserve the same source assertion and record `EVIDENCE_SPAN_EQUIVALENT`.
3. Matching orders candidates by target match, category/status, attribute/value, evidence correspondence, then stable `findingKey`. A finding/error is consumed at most once.
4. Duplicate accepted-target warnings become `DUPLICATE`; unmatched review-requiring warnings become `UNMATCHED_WARNING`; wrong-status/type warnings on the correct target become `TARGET_LINKED_MISCLASSIFICATION`; unmatched annotated errors become `FALSE_NEGATIVE`.
5. Failed, invalid-output, or interrupted cases create no fabricated matches. Their ground-truth errors remain visible; critical errors score as missed unless independently matched before terminal failure in that case execution.

## Privacy and retention constraints

Run telemetry and logs may contain IDs, hashes, versions, counts, duration, token/cost totals, and safe error codes. They must not contain source/note text, prompt bodies, raw provider output, credentials, or real healthcare information. Fixture/source text remains in the versioned synthetic benchmark repository, accessed only through its immutable reference.

