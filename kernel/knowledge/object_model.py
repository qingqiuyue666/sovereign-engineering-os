"""Knowledge object model for SEOS human-facing control layers.

The objects in this module are intentionally presentation objects. They can be
rendered to Markdown, graph JSON, or external workspace payloads, but they do not
carry execution authority and they do not replace SEOS task contracts, approval
receipts, permits, execution receipts, or evidence traces.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Mapping, Sequence
import hashlib
import json
import re

__all__ = [
    "AUTHORITY_LEVELS",
    "PROPOSAL_AUTHORITY",
    "MIRROR_AUTHORITY",
    "RECEIPT_AUTHORITY",
    "INVALID_AUTHORITY",
    "KnowledgeRelation",
    "KnowledgeObject",
    "canonical_json",
    "digest_payload",
    "now_utc",
    "safe_id",
]

PROPOSAL_AUTHORITY = "proposal"
MIRROR_AUTHORITY = "mirror"
RECEIPT_AUTHORITY = "receipt"
INVALID_AUTHORITY = "invalid"
AUTHORITY_LEVELS = frozenset({PROPOSAL_AUTHORITY, MIRROR_AUTHORITY, RECEIPT_AUTHORITY, INVALID_AUTHORITY})

_ID_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canonical_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest_payload(payload: object) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def safe_id(value: object, *, fallback: str = "object") -> str:
    text = str(value or "").strip()
    if not text:
        return fallback
    sanitized = "".join(char if char.isalnum() or char in "_.:-" else "_" for char in text)
    return sanitized.strip("._:-") or fallback


@dataclass(frozen=True)
class KnowledgeRelation:
    """A typed edge between two SEOS knowledge objects."""

    relation_type: str
    target_type: str
    target_id: str

    def __post_init__(self) -> None:
        if not self.relation_type or not self.target_type or not self.target_id:
            raise ValueError("relation_type, target_type, and target_id are required")

    def as_dict(self) -> dict[str, str]:
        return {
            "relation_type": self.relation_type,
            "target_type": self.target_type,
            "target_id": self.target_id,
        }


@dataclass(frozen=True)
class KnowledgeObject:
    """Human-facing mirror/proposal object for the knowledge layer."""

    object_type: str
    object_id: str
    authority: str
    title: str = ""
    properties: Mapping[str, object] = field(default_factory=dict)
    relations: Sequence[KnowledgeRelation] = field(default_factory=tuple)
    source: str = "seos"
    created_at: str = field(default_factory=now_utc)
    public: bool = True
    local_path_redacted: bool = True
    execution_authority_granted: bool = False

    def __post_init__(self) -> None:
        if self.authority not in AUTHORITY_LEVELS:
            raise ValueError(f"unsupported knowledge authority: {self.authority}")
        if not self.object_type or not self.object_id:
            raise ValueError("knowledge object_type and object_id are required")
        if not _ID_RE.match(self.object_type):
            raise ValueError("knowledge object_type must be identifier-like")
        if self.execution_authority_granted:
            raise ValueError("knowledge objects must not grant execution authority")

    def as_dict(self, *, include_digest: bool = False) -> dict[str, object]:
        payload = {
            "schema": "seos_knowledge_object_v1",
            "object_type": self.object_type,
            "object_id": self.object_id,
            "authority": self.authority,
            "title": self.title,
            "source": self.source,
            "created_at": self.created_at,
            "public": self.public,
            "local_path_redacted": self.local_path_redacted,
            "execution_authority_granted": self.execution_authority_granted,
            "properties": dict(self.properties),
            "relations": [relation.as_dict() for relation in self.relations],
        }
        if include_digest:
            payload["digest"] = digest_payload(payload)
        return payload

    @property
    def digest(self) -> str:
        return digest_payload(self.as_dict())

    def frontmatter(self) -> dict[str, object]:
        return {
            "schema": "seos_knowledge_object_v1",
            "seos_type": self.object_type.replace("seos.", "", 1),
            "seos_id": self.object_id,
            "title": self.title,
            "authority": self.authority,
            "source": self.source,
            "digest": self.digest,
            "public": self.public,
            "local_path_redacted": self.local_path_redacted,
            "execution_authority_granted": self.execution_authority_granted,
        }
