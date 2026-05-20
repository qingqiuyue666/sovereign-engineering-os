"""Durable human review gate for materialization final claims."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

from kernel.os_engine.database import OSDatabase, stable_content_hash, utc_now_iso, validate_no_secret_like


class HumanReviewGateError(RuntimeError):
    """Raised when human review state violates the durable gate."""


@dataclass(frozen=True, slots=True)
class HumanReviewRecord:
    review_id: str
    job_id: str
    artifact_id: str
    decision: str
    reviewer: str
    reason: str
    reviewed_at: str
    content_hash: str

    def to_dict(self) -> dict[str, Any]:
        return dict(sorted(asdict(self).items()))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))


class HumanReviewGate:
    """Review ledger where terminal decisions are immutable."""

    def __init__(self, database: OSDatabase) -> None:
        self.database = database
        self.database.initialize()

    def request_review(self, *, job_id: str, artifact_id: str, reason: str) -> HumanReviewRecord:
        if not job_id or not artifact_id:
            raise HumanReviewGateError("job_id and artifact_id are required")
        if not reason:
            raise HumanReviewGateError("review request requires reason")
        _validate_review_fields(job_id=job_id, artifact_id=artifact_id, reviewer="", reason=reason)
        review_id = stable_review_id(job_id=job_id, artifact_id=artifact_id, reason=reason)
        record = HumanReviewRecord(
            review_id=review_id,
            job_id=job_id,
            artifact_id=artifact_id,
            decision="pending",
            reviewer="",
            reason=reason,
            reviewed_at="",
            content_hash=_review_hash(
                review_id=review_id,
                job_id=job_id,
                artifact_id=artifact_id,
                decision="pending",
                reviewer="",
                reason=reason,
            ),
        )
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO human_reviews(
                    review_id,
                    job_id,
                    artifact_id,
                    decision,
                    reviewer,
                    reason,
                    reviewed_at,
                    content_hash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.review_id,
                    record.job_id,
                    record.artifact_id,
                    record.decision,
                    record.reviewer,
                    record.reason,
                    record.reviewed_at,
                    record.content_hash,
                ),
            )
        return record

    def approve_review(self, *, review_id: str, reviewer: str, reason: str = "approved") -> HumanReviewRecord:
        if not reviewer:
            raise HumanReviewGateError("approval requires reviewer")
        if not reason:
            raise HumanReviewGateError("approval requires reason")
        return self._decide(review_id=review_id, decision="approved", reviewer=reviewer, reason=reason)

    def reject_review(self, *, review_id: str, reviewer: str, reason: str) -> HumanReviewRecord:
        if not reviewer:
            raise HumanReviewGateError("rejection requires reviewer")
        if not reason:
            raise HumanReviewGateError("rejection requires reason")
        return self._decide(review_id=review_id, decision="rejected", reviewer=reviewer, reason=reason)

    def get_review(self, review_id: str) -> HumanReviewRecord | None:
        self.database.initialize()
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM human_reviews WHERE review_id = ?", (review_id,)).fetchone()
        return _record_from_row(row) if row is not None else None

    def list_reviews(self, *, job_id: str | None = None, artifact_id: str | None = None) -> list[HumanReviewRecord]:
        self.database.initialize()
        query = "SELECT * FROM human_reviews"
        clauses: list[str] = []
        args: list[str] = []
        if job_id is not None:
            clauses.append("job_id = ?")
            args.append(job_id)
        if artifact_id is not None:
            clauses.append("artifact_id = ?")
            args.append(artifact_id)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY review_id"
        with self.database.connect() as connection:
            rows = connection.execute(query, args).fetchall()
        return [_record_from_row(row) for row in rows]

    def final_claim_allowed(self, *, job_id: str, artifact_id: str) -> bool:
        reviews = self.list_reviews(job_id=job_id, artifact_id=artifact_id)
        if not reviews:
            return False
        return any(review.decision == "approved" for review in reviews)

    def require_approval(self, *, job_id: str, artifact_id: str) -> None:
        if not self.final_claim_allowed(job_id=job_id, artifact_id=artifact_id):
            raise HumanReviewGateError("required human review approval is missing")

    def _decide(self, *, review_id: str, decision: str, reviewer: str, reason: str) -> HumanReviewRecord:
        current = self.get_review(review_id)
        if current is None:
            raise HumanReviewGateError(f"review not found: {review_id}")
        if current.decision != "pending":
            raise HumanReviewGateError("review decision is immutable after terminal decision")
        _validate_review_fields(
            job_id=current.job_id,
            artifact_id=current.artifact_id,
            reviewer=reviewer,
            reason=reason,
        )
        reviewed_at = utc_now_iso()
        content_hash = _review_hash(
            review_id=current.review_id,
            job_id=current.job_id,
            artifact_id=current.artifact_id,
            decision=decision,
            reviewer=reviewer,
            reason=reason,
        )
        with self.database.connect() as connection:
            connection.execute(
                """
                UPDATE human_reviews
                SET decision = ?,
                    reviewer = ?,
                    reason = ?,
                    reviewed_at = ?,
                    content_hash = ?
                WHERE review_id = ?
                """,
                (decision, reviewer, reason, reviewed_at, content_hash, review_id),
            )
        updated = self.get_review(review_id)
        if updated is None:
            raise HumanReviewGateError("review update failed")
        return updated


def stable_review_id(*, job_id: str, artifact_id: str, reason: str) -> str:
    return f"review_{stable_content_hash({'artifact_id': artifact_id, 'job_id': job_id, 'reason': reason})[:24]}"


def _review_hash(
    *,
    review_id: str,
    job_id: str,
    artifact_id: str,
    decision: str,
    reviewer: str,
    reason: str,
) -> str:
    return stable_content_hash(
        {
            "artifact_id": artifact_id,
            "decision": decision,
            "job_id": job_id,
            "reason": reason,
            "review_id": review_id,
            "reviewer": reviewer,
        }
    )


def _validate_review_fields(*, job_id: str, artifact_id: str, reviewer: str, reason: str) -> None:
    validate_no_secret_like(
        {
            "artifact_id": artifact_id,
            "job_id": job_id,
            "reason": reason,
            "reviewer": reviewer,
        }
    )


def _record_from_row(row: Any) -> HumanReviewRecord:
    return HumanReviewRecord(
        review_id=str(row["review_id"]),
        job_id=str(row["job_id"]),
        artifact_id=str(row["artifact_id"]),
        decision=str(row["decision"]),
        reviewer=str(row["reviewer"]),
        reason=str(row["reason"]),
        reviewed_at=str(row["reviewed_at"]),
        content_hash=str(row["content_hash"]),
    )
