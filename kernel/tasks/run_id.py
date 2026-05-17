"""Deterministic task and run identifiers."""

from __future__ import annotations

from typing import Any
import hashlib
import json

__all__ = ["canonical_json", "digest_payload", "deterministic_run_id"]


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest_payload(payload: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def deterministic_run_id(*, task_id: str, policy_version: str, code_version: str, input_digest: str) -> str:
    seed = {
        "code_version": code_version,
        "input_digest": input_digest,
        "policy_version": policy_version,
        "task_id": task_id,
    }
    return "run_" + hashlib.sha256(canonical_json(seed).encode("utf-8")).hexdigest()[:24]
