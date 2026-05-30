"""Find duplicate candidates without repeatedly hashing huge files."""

from __future__ import annotations

def detect_duplicate_candidates(records: list[dict[str, object]]) -> list[dict[str, object]]:
    buckets: dict[tuple[object, object], list[dict[str, object]]] = {}
    for record in records:
        buckets.setdefault((record.get("size_bytes"), record.get("partial_sha256")), []).append(record)
    return [
        {
            "candidate_key": f"{size}:{digest}",
            "asset_ids": [str(item.get("id")) for item in items],
            "confidence": "high_partial_hash_match",
            "action": "human_review_only",
        }
        for (size, digest), items in sorted(buckets.items(), key=lambda item: str(item[0]))
        if len(items) > 1
    ]
