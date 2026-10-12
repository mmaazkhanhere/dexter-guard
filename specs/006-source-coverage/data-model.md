# Spec 006 - Data Model and Policy Contract

**Contract version:** `COVERAGE-CONTRACT-v1`  
**Coverage status policy:** `COVERAGE_STATUS-v1`  
**Expected-fact policy:** `COVERAGE_EXPECTATION-v1`

## Enumerations

```text
SourceFactCategory = SYMPTOM | MEASUREMENT | MOBILITY | CARE_ACTION | OBSERVATION | OTHER
DocumentationExpectation = REQUIRED | IMPORTANT | CONTEXTUAL
CoverageStatus = COVERED | PARTIALLY_COVERED | MISSING | DISTORTED | UNCERTAIN
RunStatus = SUCCEEDED | FAILED
MaterialAttribute = SUBJECT | POLARITY | CERTAINTY | ATTRIBUTION | TEMPORAL |
                    LATERALITY | NUMERIC_VALUE | UNIT | APPROXIMATION |
                    MOBILITY_ASSISTANCE | CARE_ACTION | OTHER
```

## Core records

```text
SourceSpan {
  sourceId: string
  sourceVersion: positive integer
  start: non-negative integer
  end: positive integer greater than start
}

ResidentContextReference {
  residentTestId: string
  source: "SPEC_001_SOURCE_DOCUMENT"
  trustLevel: "AUTHORITATIVE_TRANSCRIPT"
  version: string
  permittedUse: "TRANSCRIPT_EVIDENCE_ONLY"
}

SourceFact {
  sourceFactId: string
  sourceFactExtractionRunId: string
  sourceId: string
  sourceVersion: positive integer
  residentContext: ResidentContextReference
  sourceTextHash: SHA-256 string
  normalizationPolicy: string
  category: SourceFactCategory
  factText: string
  subject: string | null
  polarity: AFFIRMED | NEGATED | UNKNOWN
  certainty: CERTAIN | UNCERTAIN | POSSIBLE | UNKNOWN
  attribution: CARE_RECIPIENT | CAREGIVER | THIRD_PARTY | DOCUMENT_AUTHOR | UNSPECIFIED
  temporalText: string | null
  laterality: LEFT | RIGHT | BILATERAL | NONE | UNKNOWN
  numericValue: string | null
  unit: string | null
  approximation: EXACT | APPROXIMATE | UNKNOWN
  mobilityAssistance: string | null
  careAction: string | null
  documentationExpectation: DocumentationExpectation
  severityPolicyKey: string | null
  sourceSpans: SourceSpan[1..n]
}

UnresolvedSourceItem {
  unresolvedSourceItemId: string
  sourceFactExtractionRunId: string
  sourceId: string
  sourceVersion: positive integer
  residentContext: ResidentContextReference
  sourceTextHash: SHA-256 string
  normalizationPolicy: string
  candidateSourceSpans: SourceSpan[1..n]
  explanation: string
}

CoverageAssessment {
  assessmentId: string
  sourceFactId: string | null
  unresolvedSourceItemId: string | null
  status: CoverageStatus
  sourceSpans: SourceSpan[1..n]
  sourceQuotes: string[1..n]  // service-derived from validated spans
  matchedClaimIds: string[]
  preservedAttributes: MaterialAttribute[]
  missingAttributes: MaterialAttribute[]
  distortedAttributes: MaterialAttribute[]
  explanation: string
  relatedFindingRefs: RelatedFindingRef[]
}

CoverageFinding {
  coverageFindingId: string
  assessmentId: string
  sourceFactId: string | null
  unresolvedSourceItemId: string | null
  status: PARTIALLY_COVERED | MISSING | DISTORTED | UNCERTAIN
  documentationExpectation: REQUIRED | IMPORTANT | null
  severityPolicyKey: string | null
  sourceSpans: SourceSpan[1..n]
  sourceQuotes: string[1..n]  // service-derived from validated spans
  matchedClaimIds: string[]
  missingAttributes: MaterialAttribute[]
  distortedAttributes: MaterialAttribute[]
  suggestion: string
  relatedFindingRefs: RelatedFindingRef[]
  requiresReview: true
}

CoverageRun {
  coverageRunId: string
  status: SUCCEEDED | FAILED
  sourceId: string
  sourceVersion: positive integer
  residentContext: ResidentContextReference
  sourceTextHash: SHA-256 string
  normalizationPolicy: string
  noteId: string
  noteRevision: positive integer
  sourceFactExtractionRunId: string
  claimSetId: string  // immutable Spec 003 extractionRunId
  rulesetVersion: "COVERAGE-RULESET-v1"
  coverageStatusPolicyVersion: "COVERAGE_STATUS-v1"
  expectationPolicyVersion: "COVERAGE_EXPECTATION-v1"
  datasetVersion: string
  idempotencyKey: string
  correlationId: string
  providerVersion, modelVersion, promptVersion: string | null
  inputDigest: SHA-256 string
  assessments: CoverageAssessment[] // success only
  findings: CoverageFinding[]       // success only
  runtimeCounts: CoverageCounts | null
  executionMetrics: ExecutionMetrics
  failure: Failure | null
  createdAt, startedAt, completedAt: timezone-aware timestamps
}

ExecutionMetrics {
  latencyMilliseconds: non-negative integer
  retryCount: non-negative integer
  inputTokens: non-negative integer | null
  outputTokens: non-negative integer | null
  inferenceCost: decimal | null
  warningCount: non-negative integer
}
```

## Invariants

1. `SourceFact` has exactly one source ID/version pair, matching all its spans; each span resolves to the exact source substring.
2. Every source fact, unresolved item, and run carries the same resident context reference, source text hash, and normalization policy as the immutable source snapshot. The backend recomputes the hash and validates the exact span against that snapshot.
3. A `SourceFact` may not have `documentationExpectation=CONTEXTUAL` and a non-null `severityPolicyKey`.
4. An `UnresolvedSourceItem` has no `factText`, attribute values, expectation, severity key, or denominator contribution.
5. Exactly one of `sourceFactId` and `unresolvedSourceItemId` is present in an assessment/finding.
6. Every expected fact and unresolved source item appears exactly once in a successful run. Contextual facts do not need an assessment and cannot generate omission findings.
7. `COVERED` requires one or more matched claim IDs and empty missing/distorted attribute lists.
8. `PARTIALLY_COVERED` requires matched claims and one or more missing attributes.
9. `MISSING` has no matched claim IDs and no distorted attributes.
10. `DISTORTED` requires matched claims and one or more distorted attributes.
11. `UNCERTAIN` may have matched claims only when semantic comparison is unresolved. An unresolved source item always has `UNCERTAIN` and no matched claims.
12. Findings exist one-to-one with non-covered assessments. They must derive quotes from valid source spans and always set `requiresReview=true`.
13. A successful run has no failure. A failed run has no assessments, findings, or runtime counts.
14. The same idempotency key with the same request digest returns the original run; the same key with a different digest is a conflict and never starts a second run.

## Counts and metrics

```text
CoverageCounts {
  extractedExpectedFacts: non-negative integer
  coveredExpectedFacts: non-negative integer
  partiallyCoveredExpectedFacts: non-negative integer
  missingExpectedFacts: non-negative integer
  distortedExpectedFacts: non-negative integer
  uncertainExpectedFacts: non-negative integer
  unresolvedSourceItems: non-negative integer
  unresolvedSourceItemsRequireReview: true
  runtimeCompleteness: decimal | null
  metricBasis: "SYSTEM_EXTRACTED_EXPECTED_FACTS"
}

## Evaluation handoff record

Each Spec 008 fixture record must retain the exact synthetic `sourceText`, expected claim-level outcomes, source evidence references, `materiality` and Spec 007 severity-policy labels, annotation provenance, annotator/review status, disputed-label resolution, dataset version, and train/held-out split. The handoff must support raw-count denominators for critical-error recall, false-positive rate, claim classification performance, completeness, latency, inference cost, reviewer workload, omission recall, and false omission warning rate.

The run's `executionMetrics` record is content-free and is retained with the immutable run for latency, retry, token, cost, and warning observability.
```

`runtimeCompleteness` is `coveredExpectedFacts / extractedExpectedFacts` when the denominator is non-zero; otherwise it is `null`, not 100%. It is operational telemetry, never the held-out quality metric. A non-zero `unresolvedSourceItems` count always remains visible through `unresolvedSourceItemsRequireReview=true` and downstream review findings; a high runtime completeness value never authorizes approval.

Spec 008 calculates benchmark completeness with manual annotation:

```text
benchmarkCompleteness = faithfullyCoveredAnnotatedExpectedFacts / applicableAnnotatedExpectedFacts
omissionDetectionRecall = correctlyFlaggedAnnotatedOmissions / annotatedOmissions
falseOmissionWarningRate = falseOmissionWarnings / reviewedNonOmissions
```

