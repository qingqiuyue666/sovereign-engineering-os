"""Deterministic schema metadata for the Sovereign OS engine v3 brain."""

from __future__ import annotations

import hashlib
import json

SCHEMA_VERSION = 3

SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER PRIMARY KEY,
        applied_at TEXT NOT NULL,
        content_hash TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS jobs (
        job_id TEXT PRIMARY KEY,
        job_type TEXT NOT NULL,
        created_at TEXT NOT NULL,
        current_status TEXT NOT NULL,
        input_manifest_json TEXT NOT NULL,
        output_dir TEXT NOT NULL,
        human_review_required INTEGER NOT NULL,
        dry_run INTEGER NOT NULL,
        source_git_commit TEXT NOT NULL,
        local_only INTEGER NOT NULL,
        content_hash TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS job_events (
        event_id TEXT PRIMARY KEY,
        job_id TEXT NOT NULL,
        sequence INTEGER NOT NULL,
        event_type TEXT NOT NULL,
        occurred_at TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        reason TEXT,
        content_hash TEXT NOT NULL,
        UNIQUE(job_id, sequence),
        FOREIGN KEY(job_id) REFERENCES jobs(job_id) ON DELETE RESTRICT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS artifacts (
        artifact_id TEXT PRIMARY KEY,
        job_id TEXT NOT NULL,
        artifact_type TEXT NOT NULL,
        local_path TEXT NOT NULL,
        sha256 TEXT NOT NULL,
        size_bytes INTEGER NOT NULL,
        review_status TEXT NOT NULL,
        quarantine_status TEXT NOT NULL,
        quarantine_reason TEXT,
        local_only INTEGER NOT NULL,
        safe_to_publish INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        content_hash TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS materializations (
        materialization_id TEXT PRIMARY KEY,
        target_artifact_id TEXT NOT NULL,
        target_name TEXT NOT NULL,
        upstream_inputs_json TEXT NOT NULL,
        status TEXT NOT NULL,
        freshness_hash TEXT NOT NULL,
        validation_json TEXT NOT NULL,
        human_review_required INTEGER NOT NULL,
        final_claim_allowed INTEGER NOT NULL,
        content_hash TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS human_reviews (
        review_id TEXT PRIMARY KEY,
        job_id TEXT NOT NULL,
        artifact_id TEXT NOT NULL,
        decision TEXT NOT NULL,
        reviewer TEXT NOT NULL,
        reason TEXT NOT NULL,
        reviewed_at TEXT NOT NULL,
        content_hash TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_job_events_job_sequence ON job_events(job_id, sequence)",
    "CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(current_status)",
    "CREATE INDEX IF NOT EXISTS idx_artifacts_job_id ON artifacts(job_id)",
    "CREATE INDEX IF NOT EXISTS idx_materializations_target ON materializations(target_artifact_id)",
    "CREATE INDEX IF NOT EXISTS idx_human_reviews_job_artifact ON human_reviews(job_id, artifact_id)",
)


def schema_content_hash() -> str:
    """Return the stable hash for the schema text in application order."""

    encoded = json.dumps(SCHEMA_STATEMENTS, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


SCHEMA_CONTENT_HASH = schema_content_hash()
