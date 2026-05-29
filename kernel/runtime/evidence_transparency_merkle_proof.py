"""Evidence Transparency / Merkle Inclusion Proof V1.

This module implements a local-only transparency proof layer over release
evidence digests. It builds deterministic Merkle roots, emits per-item
inclusion proofs, verifies proofs locally, and binds the transparency root to
the real WAL. It does not publish roots, call networks, or read credentials.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Mapping, Sequence

from kernel.stores.real_wal_storage import FileBackedRealWalStorage

__all__ = [
    "EVIDENCE_TRANSPARENCY_MERKLE_VERSION",
    "ZERO_HASH",
    "EvidenceTransparencyError",
    "EvidenceTransparencyInclusionProof",
    "EvidenceTransparencyProofVerification",
    "EvidenceTransparencyPublication",
    "EvidenceTransparencyRootReceipt",
    "FileBackedEvidenceTransparencyMerkleLog",
    "compute_evidence_transparency_inclusion_proof_hash",
    "compute_evidence_transparency_root_receipt_hash",
    "verify_evidence_transparency_inclusion_proof",
]

EVIDENCE_TRANSPARENCY_MERKLE_VERSION = "evidence_transparency_merkle_proof_v1"
ZERO_HASH = "sha256:" + ("0" * 64)

_TASK_ID = "task-531-evidence-transparency-merkle-proof"
_WAL_RELPATH = "evidence-transparency-merkle/transparency.real-wal.jsonl"
_REPORT_RELPATH = "evidence-transparency-merkle/reports/transparency-report.json"
_RECEIPT_DIR_RELPATH = "evidence-transparency-merkle/receipts"
_PROOF_DIR_RELPATH = "evidence-transparency-merkle/proofs"
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_PAIR_POSITIONS = frozenset({"left", "right"})


class EvidenceTransparencyError(ValueError):
    """Raised when transparency evidence is malformed or contradictory."""


@dataclass(frozen=True)
class EvidenceTransparencyInclusionProof:
    proof_version: str
    item_id: str
    evidence_digest: str
    evidence_kind: str
    leaf_index: int
    leaf_hash: str
    proof_path: tuple[tuple[str, str], ...]
    root_hash: str
    proof_hash: str = ""

    def __post_init__(self) -> None:
        if self.proof_version != EVIDENCE_TRANSPARENCY_MERKLE_VERSION:
            raise EvidenceTransparencyError("proof_version_invalid")
        _require_nonempty_string(self.item_id, "item_id")
        _require_nonempty_string(self.evidence_kind, "evidence_kind")
        _require_sha256(self.evidence_digest, "evidence_digest")
        if not isinstance(self.leaf_index, int) or isinstance(self.leaf_index, bool):
            raise EvidenceTransparencyError("leaf_index_must_be_int")
        if self.leaf_index < 0:
            raise EvidenceTransparencyError("leaf_index_must_be_nonnegative")
        _require_sha256(self.leaf_hash, "leaf_hash")
        _require_sha256(self.root_hash, "root_hash")
        object.__setattr__(self, "proof_path", _normalize_proof_path(self.proof_path))
        expected_leaf = _leaf_hash(
            {
                "evidence_digest": self.evidence_digest,
                "evidence_kind": self.evidence_kind,
                "item_id": self.item_id,
            }
        )
        if self.leaf_hash != expected_leaf:
            raise EvidenceTransparencyError("leaf_hash_mismatch")
        _install_or_verify_hash(
            self,
            "proof_hash",
            compute_evidence_transparency_inclusion_proof_hash,
        )

    def deterministic_material(self) -> dict[str, object]:
        return {
            "evidence_digest": self.evidence_digest,
            "evidence_kind": self.evidence_kind,
            "item_id": self.item_id,
            "leaf_hash": self.leaf_hash,
            "leaf_index": self.leaf_index,
            "proof_path": self.proof_path,
            "proof_version": self.proof_version,
            "root_hash": self.root_hash,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["proof_hash"] = self.proof_hash
        return _json_ready(payload)  # type: ignore[return-value]


@dataclass(frozen=True)
class EvidenceTransparencyRootReceipt:
    transparency_version: str
    accepted: bool
    failures: tuple[str, ...]
    transparency_id: str
    root_hash: str
    leaf_count: int
    evidence_item_ids: tuple[str, ...]
    leaf_hashes: tuple[str, ...]
    independent_verification_receipt_hash: str
    wal_record_hash: str
    observed_at: str
    receipt_hash: str = ""

    def __post_init__(self) -> None:
        if self.transparency_version != EVIDENCE_TRANSPARENCY_MERKLE_VERSION:
            raise EvidenceTransparencyError("transparency_version_invalid")
        if not isinstance(self.accepted, bool):
            raise EvidenceTransparencyError("accepted_must_be_bool")
        object.__setattr__(self, "failures", _normalize_failures(self.failures))
        _require_nonempty_string(self.transparency_id, "transparency_id")
        _require_sha256(self.root_hash, "root_hash")
        _require_sha256(
            self.independent_verification_receipt_hash,
            "independent_verification_receipt_hash",
        )
        _require_sha256(self.wal_record_hash, "wal_record_hash")
        _require_nonempty_string(self.observed_at, "observed_at")
        if not isinstance(self.leaf_count, int) or isinstance(self.leaf_count, bool):
            raise EvidenceTransparencyError("leaf_count_must_be_int")
        if self.leaf_count < 0:
            raise EvidenceTransparencyError("leaf_count_must_be_nonnegative")
        object.__setattr__(
            self,
            "evidence_item_ids",
            _normalize_string_tuple(self.evidence_item_ids, "evidence_item_id"),
        )
        object.__setattr__(
            self,
            "leaf_hashes",
            _normalize_hash_tuple(self.leaf_hashes, "leaf_hash"),
        )
        if self.leaf_count != len(self.evidence_item_ids):
            raise EvidenceTransparencyError("leaf_count_item_count_mismatch")
        if self.leaf_count != len(self.leaf_hashes):
            raise EvidenceTransparencyError("leaf_count_hash_count_mismatch")
        expected_acceptance = (
            not self.failures
            and self.leaf_count > 0
            and self.root_hash != ZERO_HASH
            and self.wal_record_hash != ZERO_HASH
        )
        if self.accepted != expected_acceptance:
            raise EvidenceTransparencyError(
                "accepted_must_match_transparency_evidence"
            )
        _install_or_verify_hash(
            self,
            "receipt_hash",
            compute_evidence_transparency_root_receipt_hash,
        )

    def deterministic_material(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "evidence_item_ids": self.evidence_item_ids,
            "failures": self.failures,
            "independent_verification_receipt_hash": self.independent_verification_receipt_hash,
            "leaf_count": self.leaf_count,
            "leaf_hashes": self.leaf_hashes,
            "observed_at": self.observed_at,
            "root_hash": self.root_hash,
            "transparency_id": self.transparency_id,
            "transparency_version": self.transparency_version,
            "wal_record_hash": self.wal_record_hash,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["receipt_hash"] = self.receipt_hash
        return _json_ready(payload)  # type: ignore[return-value]


@dataclass(frozen=True)
class EvidenceTransparencyProofVerification:
    accepted: bool
    failures: tuple[str, ...]
    item_id: str
    root_hash: str
    proof_hash: str
    verification_hash: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.accepted, bool):
            raise EvidenceTransparencyError("accepted_must_be_bool")
        object.__setattr__(self, "failures", _normalize_failures(self.failures))
        _require_nonempty_string(self.item_id, "item_id")
        _require_sha256(self.root_hash, "root_hash")
        _require_sha256(self.proof_hash, "proof_hash")
        expected = not self.failures
        if self.accepted != expected:
            raise EvidenceTransparencyError(
                "accepted_must_match_verification_failures"
            )
        _install_or_verify_hash(self, "verification_hash", _proof_verification_hash)

    def deterministic_material(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "failures": self.failures,
            "item_id": self.item_id,
            "proof_hash": self.proof_hash,
            "root_hash": self.root_hash,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["verification_hash"] = self.verification_hash
        return _json_ready(payload)  # type: ignore[return-value]


@dataclass(frozen=True)
class EvidenceTransparencyPublication:
    root_receipt: EvidenceTransparencyRootReceipt
    inclusion_proofs: tuple[EvidenceTransparencyInclusionProof, ...]


class FileBackedEvidenceTransparencyMerkleLog:
    """Builds and persists deterministic local transparency roots and proofs."""

    def __init__(self, *, runtime_root: str | Path) -> None:
        self.runtime_root = _validate_runtime_root(Path(runtime_root))

    def publish(
        self,
        evidence_items: Sequence[Mapping[str, object]],
        *,
        transparency_id: str = "evidence-transparency-merkle-proof-531",
        independent_verification_receipt: Mapping[str, object] | str | None = None,
        observed_at: str | None = None,
    ) -> EvidenceTransparencyPublication:
        observed = _timestamp(observed_at)
        _require_nonempty_string(transparency_id, "transparency_id")
        independent_hash, independent_failures = _independent_receipt_hash(
            independent_verification_receipt
        )
        normalized_items, item_failures = _normalize_evidence_items(evidence_items)
        failures = [*independent_failures, *item_failures]
        leaf_hashes = tuple(_leaf_hash(item) for item in normalized_items)
        if not leaf_hashes:
            failures.append("evidence_items_required")
        root_hash = _merkle_root(leaf_hashes) if leaf_hashes else ZERO_HASH
        proofs = tuple(
            _proof_for_item(item, index, leaf_hashes, root_hash)
            for index, item in enumerate(normalized_items)
        )
        wal_record_hash = self._append_wal(
            accepted=not failures and bool(leaf_hashes),
            transparency_id=transparency_id,
            root_hash=root_hash,
            leaf_hashes=leaf_hashes,
            independent_verification_receipt_hash=independent_hash,
            observed_at=observed,
        )
        receipt = EvidenceTransparencyRootReceipt(
            transparency_version=EVIDENCE_TRANSPARENCY_MERKLE_VERSION,
            accepted=not failures and bool(leaf_hashes),
            failures=_dedupe(failures),
            transparency_id=transparency_id,
            root_hash=root_hash,
            leaf_count=len(leaf_hashes),
            evidence_item_ids=tuple(str(item["item_id"]) for item in normalized_items),
            leaf_hashes=leaf_hashes,
            independent_verification_receipt_hash=independent_hash,
            wal_record_hash=wal_record_hash,
            observed_at=observed,
        )
        self._persist_publication(receipt, proofs)
        return EvidenceTransparencyPublication(
            root_receipt=receipt,
            inclusion_proofs=proofs,
        )

    def _append_wal(
        self,
        *,
        accepted: bool,
        transparency_id: str,
        root_hash: str,
        leaf_hashes: tuple[str, ...],
        independent_verification_receipt_hash: str,
        observed_at: str,
    ) -> str:
        wal_path = self._resolve_relpath(_WAL_RELPATH, "wal_relpath")
        wal_path.parent.mkdir(parents=True, exist_ok=True)
        leaf_bundle_hash = _sha256_json(leaf_hashes)
        material = {
            "accepted": accepted,
            "independent_verification_receipt_hash": independent_verification_receipt_hash,
            "leaf_bundle_hash": leaf_bundle_hash,
            "root_hash": root_hash,
        }
        return FileBackedRealWalStorage(wal_path).append(
            record_type="SYSTEM_ACCEPTANCE_EVENT",
            task_id=_TASK_ID,
            run_id=transparency_id,
            payload_hash=_sha256_json(material),
            digest_bindings={
                "independent_verification_receipt_hash": independent_verification_receipt_hash,
                "leaf_bundle_hash": leaf_bundle_hash,
                "transparency_root_hash": root_hash,
            },
            created_at=observed_at,
        ).record_hash

    def _persist_publication(
        self,
        receipt: EvidenceTransparencyRootReceipt,
        proofs: tuple[EvidenceTransparencyInclusionProof, ...],
    ) -> None:
        report = {
            "accepted": receipt.accepted,
            "failures": receipt.failures,
            "independent_verification_receipt_hash": receipt.independent_verification_receipt_hash,
            "inclusion_proof_count": len(proofs),
            "leaf_count": receipt.leaf_count,
            "receipt_hash": receipt.receipt_hash,
            "root_hash": receipt.root_hash,
            "wal_record_hash": receipt.wal_record_hash,
        }
        self._write_new_json(_REPORT_RELPATH, report)
        receipt_relpath = (
            _RECEIPT_DIR_RELPATH
            + "/"
            + receipt.receipt_hash.removeprefix("sha256:")
            + ".json"
        )
        self._write_new_json(receipt_relpath, receipt.as_dict())
        for proof in proofs:
            proof_relpath = (
                _PROOF_DIR_RELPATH
                + "/"
                + _safe_name(proof.item_id)
                + "-"
                + proof.proof_hash.removeprefix("sha256:")
                + ".json"
            )
            self._write_new_json(proof_relpath, proof.as_dict())

    def _write_new_json(self, relpath: str, payload: object) -> None:
        path = self._resolve_relpath(relpath, "output_relpath")
        if path.exists():
            raise EvidenceTransparencyError("output_already_exists")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                _json_ready(payload),
                sort_keys=True,
                indent=2,
                ensure_ascii=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def _resolve_relpath(self, relpath: str, field_name: str) -> Path:
        if not isinstance(relpath, str) or not relpath:
            raise EvidenceTransparencyError(
                field_name + "_must_be_nonempty_string"
            )
        if "\\" in relpath:
            raise EvidenceTransparencyError(field_name + "_backslash_forbidden")
        pure = PurePosixPath(relpath)
        if pure.is_absolute() or ".." in pure.parts:
            raise EvidenceTransparencyError(
                field_name + "_must_stay_under_runtime_root"
            )
        path = (self.runtime_root / pure).resolve(strict=False)
        root = self.runtime_root.resolve()
        if path != root and root not in path.parents:
            raise EvidenceTransparencyError(field_name + "_escapes_runtime_root")
        return path


def verify_evidence_transparency_inclusion_proof(
    proof: EvidenceTransparencyInclusionProof | Mapping[str, object],
    root_receipt: EvidenceTransparencyRootReceipt | Mapping[str, object],
) -> EvidenceTransparencyProofVerification:
    parsed_proof = _proof_from_mapping(proof)
    parsed_receipt = _root_receipt_from_mapping(root_receipt)
    failures: list[str] = []
    if parsed_proof.root_hash != parsed_receipt.root_hash:
        failures.append("proof_root_hash_mismatch")
    if parsed_proof.item_id not in parsed_receipt.evidence_item_ids:
        failures.append("unknown_evidence_item")
    else:
        expected_index = parsed_receipt.evidence_item_ids.index(parsed_proof.item_id)
        if parsed_proof.leaf_index != expected_index:
            failures.append("proof_order_mismatch")
        elif parsed_receipt.leaf_hashes[expected_index] != parsed_proof.leaf_hash:
            failures.append("leaf_digest_changed")
    recomputed = _recompute_root_from_proof(parsed_proof)
    if recomputed != parsed_receipt.root_hash:
        failures.append("tampered_inclusion_proof")
    return EvidenceTransparencyProofVerification(
        accepted=not failures,
        failures=_dedupe(failures),
        item_id=parsed_proof.item_id,
        root_hash=parsed_receipt.root_hash,
        proof_hash=parsed_proof.proof_hash,
    )


def compute_evidence_transparency_inclusion_proof_hash(
    proof: EvidenceTransparencyInclusionProof,
) -> str:
    return _sha256_json(proof.deterministic_material())


def compute_evidence_transparency_root_receipt_hash(
    receipt: EvidenceTransparencyRootReceipt,
) -> str:
    return _sha256_json(receipt.deterministic_material())


def _normalize_evidence_items(
    evidence_items: Sequence[Mapping[str, object]],
) -> tuple[tuple[dict[str, object], ...], tuple[str, ...]]:
    if not isinstance(evidence_items, Sequence) or isinstance(evidence_items, (str, bytes)):
        raise EvidenceTransparencyError("evidence_items_must_be_sequence")
    normalized: list[dict[str, object]] = []
    failures: list[str] = []
    seen_ids: set[str] = set()
    for item in evidence_items:
        if not isinstance(item, Mapping):
            failures.append("evidence_item_must_be_mapping")
            continue
        item_id = item.get("item_id")
        evidence_digest = item.get("evidence_digest")
        evidence_kind = item.get("evidence_kind", "release_evidence")
        if not isinstance(item_id, str) or not item_id.strip():
            failures.append("evidence_item_id_required")
            continue
        if item_id in seen_ids:
            failures.append("duplicate_evidence_item_id:" + item_id)
            continue
        seen_ids.add(item_id)
        if not isinstance(evidence_digest, str) or not _SHA256_PATTERN.match(evidence_digest):
            failures.append("evidence_digest_invalid:" + item_id)
            continue
        if not isinstance(evidence_kind, str) or not evidence_kind.strip():
            failures.append("evidence_kind_required:" + item_id)
            continue
        normalized.append(
            {
                "evidence_digest": evidence_digest,
                "evidence_kind": evidence_kind,
                "item_id": item_id,
            }
        )
    canonical = tuple(
        sorted(
            normalized,
            key=lambda value: (
                str(value["item_id"]),
                str(value["evidence_digest"]),
                str(value["evidence_kind"]),
            ),
        )
    )
    return canonical, tuple(_dedupe(failures))


def _independent_receipt_hash(
    receipt: Mapping[str, object] | str | None,
) -> tuple[str, tuple[str, ...]]:
    if receipt is None:
        return ZERO_HASH, ()
    if isinstance(receipt, str):
        if not _SHA256_PATTERN.match(receipt):
            return ZERO_HASH, ("independent_verification_receipt_hash_invalid",)
        return receipt, ()
    if not isinstance(receipt, Mapping):
        return ZERO_HASH, ("independent_verification_receipt_must_be_mapping",)
    receipt_hash = receipt.get("receipt_hash")
    if not isinstance(receipt_hash, str) or not _SHA256_PATTERN.match(receipt_hash):
        return ZERO_HASH, ("independent_verification_receipt_hash_invalid",)
    if receipt.get("accepted") is not True:
        return receipt_hash, ("independent_verification_receipt_not_accepted",)
    return receipt_hash, ()


def _proof_for_item(
    item: Mapping[str, object],
    index: int,
    leaf_hashes: tuple[str, ...],
    root_hash: str,
) -> EvidenceTransparencyInclusionProof:
    return EvidenceTransparencyInclusionProof(
        proof_version=EVIDENCE_TRANSPARENCY_MERKLE_VERSION,
        item_id=str(item["item_id"]),
        evidence_digest=str(item["evidence_digest"]),
        evidence_kind=str(item["evidence_kind"]),
        leaf_index=index,
        leaf_hash=leaf_hashes[index],
        proof_path=_proof_path_for_index(leaf_hashes, index),
        root_hash=root_hash,
    )


def _proof_path_for_index(
    leaf_hashes: tuple[str, ...],
    index: int,
) -> tuple[tuple[str, str], ...]:
    path: list[tuple[str, str]] = []
    level = tuple(leaf_hashes)
    current_index = index
    while len(level) > 1:
        sibling_index = current_index - 1 if current_index % 2 else current_index + 1
        if sibling_index < len(level):
            position = "left" if sibling_index < current_index else "right"
            path.append((position, level[sibling_index]))
        current_index //= 2
        level = _next_merkle_level(level)
    return tuple(path)


def _recompute_root_from_proof(proof: EvidenceTransparencyInclusionProof) -> str:
    current = proof.leaf_hash
    for position, sibling_hash in proof.proof_path:
        if position == "left":
            current = _node_hash(sibling_hash, current)
        elif position == "right":
            current = _node_hash(current, sibling_hash)
        else:
            raise EvidenceTransparencyError("proof_position_invalid")
    return current


def _merkle_root(leaf_hashes: tuple[str, ...]) -> str:
    if not leaf_hashes:
        return ZERO_HASH
    level = tuple(leaf_hashes)
    while len(level) > 1:
        level = _next_merkle_level(level)
    return level[0]


def _next_merkle_level(level: tuple[str, ...]) -> tuple[str, ...]:
    next_level: list[str] = []
    for index in range(0, len(level), 2):
        left = level[index]
        if index + 1 >= len(level):
            next_level.append(left)
        else:
            next_level.append(_node_hash(left, level[index + 1]))
    return tuple(next_level)


def _leaf_hash(item: Mapping[str, object]) -> str:
    return _sha256_json(
        {
            "evidence_digest": item.get("evidence_digest"),
            "evidence_kind": item.get("evidence_kind", "release_evidence"),
            "item_id": item.get("item_id"),
            "leaf_version": EVIDENCE_TRANSPARENCY_MERKLE_VERSION,
        }
    )


def _node_hash(left_hash: str, right_hash: str) -> str:
    _require_sha256(left_hash, "left_hash")
    _require_sha256(right_hash, "right_hash")
    return _sha256_json(
        {
            "left": left_hash,
            "node_version": EVIDENCE_TRANSPARENCY_MERKLE_VERSION,
            "right": right_hash,
        }
    )


def _proof_from_mapping(
    proof: EvidenceTransparencyInclusionProof | Mapping[str, object],
) -> EvidenceTransparencyInclusionProof:
    if isinstance(proof, EvidenceTransparencyInclusionProof):
        return proof
    if not isinstance(proof, Mapping):
        raise EvidenceTransparencyError("proof_must_be_mapping")
    return EvidenceTransparencyInclusionProof(
        proof_version=str(proof.get("proof_version", "")),
        item_id=str(proof.get("item_id", "")),
        evidence_digest=str(proof.get("evidence_digest", "")),
        evidence_kind=str(proof.get("evidence_kind", "")),
        leaf_index=proof.get("leaf_index"),  # type: ignore[arg-type]
        leaf_hash=str(proof.get("leaf_hash", "")),
        proof_path=proof.get("proof_path", ()),  # type: ignore[arg-type]
        root_hash=str(proof.get("root_hash", "")),
        proof_hash=str(proof.get("proof_hash", "")),
    )


def _root_receipt_from_mapping(
    receipt: EvidenceTransparencyRootReceipt | Mapping[str, object],
) -> EvidenceTransparencyRootReceipt:
    if isinstance(receipt, EvidenceTransparencyRootReceipt):
        return receipt
    if not isinstance(receipt, Mapping):
        raise EvidenceTransparencyError("root_receipt_must_be_mapping")
    return EvidenceTransparencyRootReceipt(
        transparency_version=str(receipt.get("transparency_version", "")),
        accepted=receipt.get("accepted"),  # type: ignore[arg-type]
        failures=receipt.get("failures", ()),  # type: ignore[arg-type]
        transparency_id=str(receipt.get("transparency_id", "")),
        root_hash=str(receipt.get("root_hash", "")),
        leaf_count=receipt.get("leaf_count"),  # type: ignore[arg-type]
        evidence_item_ids=receipt.get("evidence_item_ids", ()),  # type: ignore[arg-type]
        leaf_hashes=receipt.get("leaf_hashes", ()),  # type: ignore[arg-type]
        independent_verification_receipt_hash=str(
            receipt.get("independent_verification_receipt_hash", "")
        ),
        wal_record_hash=str(receipt.get("wal_record_hash", "")),
        observed_at=str(receipt.get("observed_at", "")),
        receipt_hash=str(receipt.get("receipt_hash", "")),
    )


def _normalize_proof_path(
    values: Sequence[Sequence[str]],
) -> tuple[tuple[str, str], ...]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise EvidenceTransparencyError("proof_path_must_be_sequence")
    normalized: list[tuple[str, str]] = []
    for item in values:
        if (
            not isinstance(item, Sequence)
            or isinstance(item, (str, bytes))
            or len(item) != 2
        ):
            raise EvidenceTransparencyError("proof_path_entry_invalid")
        position = str(item[0])
        sibling_hash = str(item[1])
        if position not in _PAIR_POSITIONS:
            raise EvidenceTransparencyError("proof_path_position_invalid")
        _require_sha256(sibling_hash, "sibling_hash")
        normalized.append((position, sibling_hash))
    return tuple(normalized)


def _proof_verification_hash(
    verification: EvidenceTransparencyProofVerification,
) -> str:
    return _sha256_json(verification.deterministic_material())


def _timestamp(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    _require_nonempty_string(value, "observed_at")
    return value


def _validate_runtime_root(path: Path) -> Path:
    resolved = path.resolve(strict=False)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def _json_ready(value: object) -> object:
    try:
        return json.loads(
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
                allow_nan=False,
            )
        )
    except (TypeError, ValueError) as exc:
        raise EvidenceTransparencyError("value_must_be_json_serializable") from exc


def _sha256_json(value: object) -> str:
    encoded = json.dumps(
        _json_ready(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _require_nonempty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise EvidenceTransparencyError(field_name + "_must_be_nonempty_string")


def _require_sha256(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not _SHA256_PATTERN.match(value):
        raise EvidenceTransparencyError(field_name + "_must_be_sha256")


def _normalize_failures(values: Sequence[str]) -> tuple[str, ...]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise EvidenceTransparencyError("failures_must_be_sequence")
    normalized = tuple(str(value) for value in values)
    for value in normalized:
        _require_nonempty_string(value, "failure")
    return tuple(_dedupe(normalized))


def _normalize_string_tuple(values: Sequence[str], field_name: str) -> tuple[str, ...]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise EvidenceTransparencyError(field_name + "s_must_be_sequence")
    normalized = tuple(str(value) for value in values)
    for value in normalized:
        _require_nonempty_string(value, field_name)
    return normalized


def _normalize_hash_tuple(values: Sequence[str], field_name: str) -> tuple[str, ...]:
    normalized = _normalize_string_tuple(values, field_name)
    for value in normalized:
        _require_sha256(value, field_name)
    return normalized


def _install_or_verify_hash(instance: object, field_name: str, compute) -> None:
    current = getattr(instance, field_name)
    expected = compute(instance)
    if current in ("", None):
        object.__setattr__(instance, field_name, expected)
        return
    if current != expected:
        raise EvidenceTransparencyError(field_name + "_mismatch")


def _safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "evidence-item"


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            output.append(value)
    return tuple(output)
