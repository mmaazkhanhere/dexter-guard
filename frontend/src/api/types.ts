export type Classification = "SUPPORTED" | "UNSUPPORTED" | "CONTRADICTED" | "UNCERTAIN";
export type Severity = "CRITICAL" | "MAJOR" | "MINOR";

export type SourceDocument = {
  source_id: string; source_version: number; resident_test_id: string; language: "de-DE";
  transcript_text: string; created_at: string;
};

export type SavedExample = {
  exampleId: string; title: string; sourceId: string; sourceVersion: number;
  kind: "DOCUMENTATION" | "EVALUATION_HISTORICAL"; evaluationRunId: string | null;
  syntheticOnly: true; candidateNote?: string;
};

export type NursingFact = {
  factId: string; noteId: string; revision: number; type: "OBSERVATION" | "SYMPTOM" | "MEASUREMENT" | "ACTION";
  statement: string; residentSubject: string; sourceAnchor: Record<string, string | number | null>;
  polarity?: "AFFIRMED" | "NEGATED"; certainty?: "CERTAIN" | "UNCERTAIN"; numericValue?: string; unit?: string;
  provenance: "GENERATED_FROM_SOURCE" | "EXTERNALLY_SUPPLIED";
};

export type NoteResponse = {
  noteId: string; revision: number; previousRevisionId?: string; content: string; status: "DRAFT";
  origin: "GENERATED" | "IMPORTED"; sourceId: string; sourceVersion: number; validationRunId: string;
  facts: NursingFact[]; generationRunId?: string; modelId?: string; promptVersion?: string;
  schemaVersion: string; rulesetVersion: string; sourceTextHash: string; normalizationPolicy: string;
  createdAt: string; createdBy: string; externalOrigin?: { system: string; externalNoteId: string };
};

export type SourceSpan = { sourceId: string; sourceVersion: number; start: number; end: number };
export type NoteSpan = { startCodePoint: number; endCodePointExclusive: number; text: string };
export type Finding = {
  reviewFindingId: string; origin: string; originRunId?: string; originFindingId?: string;
  noteId: string; noteRevision: number; sourceId: string; sourceVersion: number; claimId?: string;
  claimSpan?: NoteSpan; upstreamStatus?: string; ruleCode?: string; severity: Severity;
  severityPolicyVersion: string; severityRationale: string; explanation: string;
  evidence: { availability: "AVAILABLE" | "MISSING" | "INVALID"; spans: SourceSpan[]; excerpts: string[] };
  state: "OPEN" | "RESOLVED" | "ADJUDICATED" | "STALE"; createdAt: string;
};
export type Suggestion = { suggestionId: string; findingId: string; noteId: string; baseRevision: number; replacement: string; targetNoteSpan: NoteSpan; supportStatus: "USABLE" | "UNUSABLE" | "REJECTED"; supportSpans: SourceSpan[]; generatedBy: string; createdAt: string };
export type ReviewContext = {
  contractVersion: string; noteId: string; revision: number; latestRevision: number; noteStatus: string;
  source: { sourceId: string; sourceVersion: number }; transcriptText: string; candidateNote: string;
  findings: Finding[]; decisions: ReviewDecision[]; suggestions: Suggestion[]; fullVerification: FullVerification | null;
  approvalEligible: boolean;
};
export type ReviewDecision = { reviewDecisionId: string; findingId: string; noteId: string; noteRevision: number; kind: string; outcome: string; reviewerLabel: string; rationale?: string; recordedAt: string };
export type AuditEvent = { eventId: string; sequence: number; occurredAt: string; actorLabel: string; eventType: string; noteId: string; noteRevision: number; targetType: string; targetId: string; references: string[]; payloadDigest: string; rationale?: string };
export type AuditResponse = { contractVersion: string; noteId: string; events: AuditEvent[] };
export type FullVerification = { fullVerificationId: string; noteId: string; noteRevision: number; status: "VALID" | "INVALID" | "FAILED"; failureCode?: string; failureMessage?: string; componentStatuses: { component: string; runId?: string; status: string; failureCode?: string }[]; createdAt: string; completedAt?: string };
export type EvaluationMetric = { metricId: string; metricKind: "RATE" | "COUNT_PER_NOTE" | "DURATION_DISTRIBUTION" | "COST_DISTRIBUTION"; state: string; scorableCount: number; unscorableCount: number; failedCount: number; reason?: string; numerator?: number; denominator?: number; value?: number; count?: number; noteCount?: number; valuePerNote?: number; unit?: string; observationCount?: number; p50?: number; p95?: number; mean?: number };
export type EvaluationSummary = { evaluationRunId: string; origin: string; runStatus: string; dataset?: { datasetId?: string; datasetVersion?: string; datasetHash?: string; selectedSplit?: string }; metrics: EvaluationMetric[]; failures?: Record<string, unknown>; falseNegativeCaseIds?: string[]; missedCriticalCases?: unknown[]; historicalOrLive?: string };
export type EvaluationCase = { caseExecutionId: string; scenarioId: string; candidateId: string; status: string; observedFindings: Array<Record<string, unknown>>; matchResults: Array<Record<string, unknown>>; completenessResults: Array<Record<string, unknown>>; latency?: { endToEndMilliseconds?: number }; usageAndCost?: { costState?: string; estimatedCost?: number; currency?: string } };
export type EvaluationRun = { evaluationRunId: string; origin: string; runPurpose?: string; scoringState?: string; status: string; datasetId?: string; datasetVersion?: string; selectedSplit?: string; aggregateMetrics?: EvaluationMetric[]; caseResults?: EvaluationCase[]; configuration?: Record<string, unknown>; comparison?: { status: string; baselineRunId: string; validatedRunId: string; aggregateDeltas: Array<Record<string, unknown>> } | null };
