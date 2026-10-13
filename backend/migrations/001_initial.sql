CREATE TABLE IF NOT EXISTS source_documents (
    source_id TEXT NOT NULL,
    source_version INTEGER NOT NULL CHECK (source_version >= 1),
    resident_test_id TEXT NOT NULL,
    language TEXT NOT NULL CHECK (language = 'de-DE'),
    transcript_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (source_id, source_version)
);

CREATE TABLE IF NOT EXISTS note_revisions (
    note_id TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (revision >= 1),
    previous_revision_id TEXT,
    content TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status = 'DRAFT'),
    origin TEXT NOT NULL CHECK (origin IN ('GENERATED', 'IMPORTED')),
    source_id TEXT NOT NULL,
    source_version INTEGER NOT NULL CHECK (source_version >= 1),
    external_origin_json JSONB,
    validation_run_id TEXT NOT NULL,
    generation_run_id TEXT,
    model_id TEXT,
    prompt_version TEXT,
    schema_version TEXT NOT NULL,
    ruleset_version TEXT NOT NULL,
    source_text_hash TEXT NOT NULL,
    normalization_policy TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    created_by TEXT NOT NULL,
    PRIMARY KEY (note_id, revision),
    CHECK ((origin = 'IMPORTED') = (external_origin_json IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS nursing_facts (
    note_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    fact_index INTEGER NOT NULL CHECK (fact_index >= 1),
    payload_json JSONB NOT NULL,
    PRIMARY KEY (note_id, revision, fact_index),
    FOREIGN KEY (note_id, revision) REFERENCES note_revisions(note_id, revision) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS review_audit_events (
    event_id TEXT PRIMARY KEY,
    note_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    payload_json JSONB NOT NULL,
    UNIQUE(note_id, sequence)
);

CREATE TABLE IF NOT EXISTS review_notes (
    note_key TEXT PRIMARY KEY,
    payload_json JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS review_findings (
    finding_id TEXT PRIMARY KEY,
    payload_json JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS review_decisions (
    decision_id TEXT PRIMARY KEY,
    payload_json JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS review_suggestions (
    suggestion_id TEXT PRIMARY KEY,
    payload_json JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS review_verifications (
    verification_id TEXT PRIMARY KEY,
    payload_json JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS review_claim_feedback (
    feedback_id TEXT PRIMARY KEY,
    payload_json JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS review_dispositions (
    disposition_id TEXT PRIMARY KEY,
    payload_json JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS review_idempotency (
    operation TEXT NOT NULL,
    key TEXT NOT NULL,
    digest TEXT NOT NULL,
    PRIMARY KEY (operation, key)
);

CREATE TABLE IF NOT EXISTS evaluation_datasets (
    dataset_id TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    PRIMARY KEY (dataset_id, dataset_version)
);

CREATE TABLE IF NOT EXISTS evaluation_idempotency (
    idempotency_key TEXT PRIMARY KEY,
    input_digest TEXT NOT NULL,
    evaluation_run_id TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS evaluation_runs (
    evaluation_run_id TEXT PRIMARY KEY,
    payload_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);
