"""Release Ceremony / Tagging Artifact Gate V1.

Prepares local release ceremony artifacts after #529 and the post-#529
verification chain. The gate verifies upstream receipts, writes a release
notes draft, emits a tag command proposal, and records the decision in the
real WAL. It does not create tags, push tags, publish releases, call networks,
or read credentials.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Mapping, Sequence

from kernel.stores.real_wal_storage import FileBackedRealWalStorage

__all__ = [
    "RELEASE_CEREMONY_TAGGING_ARTIFACT_GATE_VERSION",
    "ZERO_HASH",
    "FileBackedReleaseCeremonyTaggingArtifactGate",
    "ReleaseCeremonyGateError",
    "ReleaseCeremonyReceipt",
    "compute_release_ceremony_receipt_hash",
]

RELEASE_CEREMONY_TAGGING_ARTIFACT_GATE_VERSION = (
    "release_ceremony_tagging_artifact_gate_v1"
)
ZERO_HASH = "sha256:" + ("0" * 64)
ZERO_HEAD = "0" * 40

_TASK_ID = "task-534-release-ceremony-tagging-artifact-gate"
_FINAL_SIGNOFF_VERSION = "release_candidate_final_signoff_v1"
_INDEPENDENT_VERIFICATION_VERSION = "independent_final_signoff_verification_v1"
_TRANSPARENCY_VERSION = "evidence_transparency_merkle_proof_v1"
_POLICY_VERSION = "declarative_policy_gate_bundle_v1"
_FAULT_SIMULATION_VERSION = "deterministic_fault_simulation_harness_v1"
_FINAL_VERDICT = "READY_TO_REVIEW_AND_MERGE"
_WAL_RELPATH = "release-ceremony-tagging/release-ceremony.real-wal.jsonl"
_REPORT_RELPATH = "release-ceremony-tagging/reports/release-ceremony-report.json"
_RECEIPT_DIR_RELPATH = "release-ceremony-tagging/receipts"
_RELEASE_NOTES_RELPATH = (
    "release-ceremony-tagging/release-notes/release-notes-draft.md"
)
_TAG_COMMAND_RELPATH = (
    "release-ceremony-tagging/tag-command/tag-command-proposal.json"
)
_RELEASE_TAG_PATTERN = re.compile(r"^v\d+\.\d+\.\d+-rc\.529(?:\+[0-9a-f]{7,40})?$")
_SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
_HEAD_PATTERN = re.compile(r"^[0-9a-f]{40}$")

_UPSTREAM_KEYS = (
    "final_signoff_receipt",
    "independent_verification_receipt",
    "transparency_root_receipt",
    "policy_decision_receipt",
    "fault_simulation_report",
)
_OPTIONAL_UPSTREAM_FILES = {
    "independent_verification_receipt": (
        "kernel/runtime/independent_final_signoff_verification.py"
    ),
    "transparency_root_receipt": (
        "kernel/runtime/evidence_transparency_merkle_proof.py"
    ),
    "policy_decision_receipt": (
        "kernel/runtime/declarative_policy_gate_bundle.py"
    ),
    "fault_simulation_report": (
        "kernel/runtime/deterministic_fault_simulation_harness.py"
    ),
}


class ReleaseCeremonyGateError(ValueError):
    """Raised when release ceremony evidence is malformed."""


@dataclass(frozen=True)
class ReleaseCeremonyReceipt:
    release_version: str
    accepted: bool
    failures: tuple[str, ...]
    release_id: str
    expected_main_head: str
    current_main_head: str
    release_tag_proposal: str
    final_signoff_receipt_hash: str
    independent_verification_receipt_hash: str
    transparency_root_hash: str
    policy_decision_receipt_hash: str
    fault_simulation_report_hash: str
    release_notes_digest: str
    release_notes_relpath: str
    tag_command_digest: str
    tag_command_proposal: str
    tag_command_proposal_relpath: str
    tag_created: bool
    tag_pushed: bool
    external_artifacts_published: bool
    wal_record_hash: str
    observed_at: str
    receipt_hash: str = ""

    def __post_init__(self) -> None:
        if self.release_version != RELEASE_CEREMONY_TAGGING_ARTIFACT_GATE_VERSION:
            raise ReleaseCeremonyGateError("release_version_invalid")
        if not isinstance(self.accepted, bool):
            raise ReleaseCeremonyGateError("accepted_must_be_bool")
        object.__setattr__(self, "failures", _normalize_strings(self.failures, "failure"))
        _require_nonempty_string(self.release_id, "release_id")
        _require_head(self.expected_main_head, "expected_main_head")
        _require_head(self.current_main_head, "current_main_head")
        _require_nonempty_string(self.release_tag_proposal, "release_tag_proposal")
        for field_name in (
            "final_signoff_receipt_hash",
            "independent_verification_receipt_hash",
            "transparency_root_hash",
            "policy_decision_receipt_hash",
            "fault_simulation_report_hash",
            "release_notes_digest",
            "tag_command_digest",
            "wal_record_hash",
        ):
            _require_sha256(getattr(self, field_name), field_name)
        for field_name in (
            "release_notes_relpath",
            "tag_command_proposal",
            "tag_command_proposal_relpath",
            "observed_at",
        ):
            _require_nonempty_string(getattr(self, field_name), field_name)
        for field_name in (
            "tag_created",
            "tag_pushed",
            "external_artifacts_published",
        ):
            if not isinstance(getattr(self, field_name), bool):
                raise ReleaseCeremonyGateError(field_name + "_must_be_bool")
        expected_acceptance = (
            not self.failures
            and self.expected_main_head == self.current_main_head
            and self.final_signoff_receipt_hash != ZERO_HASH
            and self.independent_verification_receipt_hash != ZERO_HASH
            and self.transparency_root_hash != ZERO_HASH
            and self.policy_decision_receipt_hash != ZERO_HASH
            and self.fault_simulation_report_hash != ZERO_HASH
            and self.release_notes_digest != ZERO_HASH
            and self.tag_command_digest != ZERO_HASH
            and not self.tag_created
            and not self.tag_pushed
            and not self.external_artifacts_published
            and self.wal_record_hash != ZERO_HASH
        )
        if self.accepted != expected_acceptance:
            raise ReleaseCeremonyGateError(
                "accepted_must_match_release_ceremony_evidence"
            )
        _install_or_verify_hash(self, "receipt_hash", compute_release_ceremony_receipt_hash)

    def deterministic_material(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "current_main_head": self.current_main_head,
            "expected_main_head": self.expected_main_head,
            "external_artifacts_published": self.external_artifacts_published,
            "failures": self.failures,
            "fault_simulation_report_hash": self.fault_simulation_report_hash,
            "final_signoff_receipt_hash": self.final_signoff_receipt_hash,
            "independent_verification_receipt_hash": self.independent_verification_receipt_hash,
            "observed_at": self.observed_at,
            "policy_decision_receipt_hash": self.policy_decision_receipt_hash,
            "release_id": self.release_id,
            "release_notes_digest": self.release_notes_digest,
            "release_notes_relpath": self.release_notes_relpath,
            "release_tag_proposal": self.release_tag_proposal,
            "release_version": self.release_version,
            "tag_command_digest": self.tag_command_digest,
            "tag_command_proposal": self.tag_command_proposal,
            "tag_command_proposal_relpath": self.tag_command_proposal_relpath,
            "tag_created": self.tag_created,
            "tag_pushed": self.tag_pushed,
            "transparency_root_hash": self.transparency_root_hash,
            "wal_record_hash": self.wal_record_hash,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["receipt_hash"] = self.receipt_hash
        return _json_ready(payload)  # type: ignore[return-value]


class FileBackedReleaseCeremonyTaggingArtifactGate:
    """Prepares local release ceremony artifacts without mutating git state."""

    def __init__(
        self,
        *,
        runtime_root: str | Path,
        repo_root: str | Path | None = None,
    ) -> None:
        self.runtime_root = _validate_runtime_root(Path(runtime_root))
        self.repo_root = Path(repo_root or Path.cwd()).resolve(strict=False)

    def prepare(
        self,
        evidence: Mapping[str, object],
        *,
        observed_at: str | None = None,
    ) -> ReleaseCeremonyReceipt:
        if not isinstance(evidence, Mapping):
            raise ReleaseCeremonyGateError("evidence_must_be_mapping")
        observed = _timestamp(observed_at)
        data = _json_ready(evidence)
        if not isinstance(data, Mapping):
            raise ReleaseCeremonyGateError("evidence_must_be_mapping")

        release_id = _string_field(
            data,
            "release_id",
            "post-529-release-ceremony-534",
        )
        required_upstreams = self._required_upstreams(data.get("required_upstreams"))
        upstreams = {
            key: self._load_upstream_mapping(data, key)
            for key in _UPSTREAM_KEYS
        }
        failures: list[str] = []
        for key in required_upstreams:
            if upstreams[key] is None:
                failures.append("missing_upstream_receipt:" + key)

        final_signoff = upstreams["final_signoff_receipt"] or {}
        release_tag = _string_field(
            data,
            "release_tag_proposal",
            _string_field(final_signoff, "release_tag_proposal", ""),
        )
        expected_head = _normalized_head(
            data.get("expected_main_head", final_signoff.get("main_head", "")),
            failures,
            "expected_main_head",
        )
        current_head = _normalized_head(
            data.get("current_main_head", data.get("current_repo_head", None))
            or self._read_current_head(),
            failures,
            "current_main_head",
        )

        failures.extend(_release_tag_failures(release_tag))
        if expected_head != current_head:
            failures.append("main_head_mismatch")
        if data.get("release_tag_created") is True or final_signoff.get("release_tag_created") is True:
            failures.append("release_tag_must_be_proposal_only")
        if data.get("tag_push_requested") is True or data.get("push_tag") is True:
            failures.append("tag_push_must_not_be_requested")
        if data.get("external_publish_requested") is True:
            failures.append("external_publish_must_not_be_requested")

        final_hash, final_failures = _verify_final_signoff(final_signoff, release_tag)
        independent_hash, independent_failures = _verify_independent_verification(
            upstreams["independent_verification_receipt"]
        )
        transparency_hash, transparency_failures = _verify_transparency_root(
            upstreams["transparency_root_receipt"]
        )
        policy_hash, policy_failures = _verify_policy_decision(
            upstreams["policy_decision_receipt"]
        )
        fault_hash, fault_failures = _verify_fault_simulation(
            upstreams["fault_simulation_report"]
        )
        failures.extend(final_failures)
        failures.extend(independent_failures)
        failures.extend(transparency_failures)
        failures.extend(policy_failures)
        failures.extend(fault_failures)

        notes_text = _release_notes_text(
            release_id=release_id,
            release_tag=release_tag,
            expected_head=expected_head,
            observed_at=observed,
            upstream_hashes={
                "final_signoff_receipt_hash": final_hash,
                "independent_verification_receipt_hash": independent_hash,
                "transparency_root_hash": transparency_hash,
                "policy_decision_receipt_hash": policy_hash,
                "fault_simulation_report_hash": fault_hash,
            },
        )
        release_notes_digest = _sha256_text(notes_text)
        tag_command = _tag_command_proposal(release_tag, expected_head)
        tag_command_digest = _sha256_json(
            {
                "command": tag_command,
                "proposal_only": True,
                "tag_created": False,
                "tag_pushed": False,
            }
        )

        unique_failures = _dedupe(failures)
        wal_record_hash = self._append_wal(
            accepted=not unique_failures,
            release_id=release_id,
            release_tag=release_tag,
            expected_head=expected_head,
            current_head=current_head,
            release_notes_digest=release_notes_digest,
            tag_command_digest=tag_command_digest,
            upstream_hashes={
                "final_signoff_receipt_hash": final_hash,
                "independent_verification_receipt_hash": independent_hash,
                "transparency_root_hash": transparency_hash,
                "policy_decision_receipt_hash": policy_hash,
                "fault_simulation_report_hash": fault_hash,
            },
            observed_at=observed,
        )
        receipt = ReleaseCeremonyReceipt(
            release_version=RELEASE_CEREMONY_TAGGING_ARTIFACT_GATE_VERSION,
            accepted=not unique_failures,
            failures=unique_failures,
            release_id=release_id,
            expected_main_head=expected_head,
            current_main_head=current_head,
            release_tag_proposal=release_tag,
            final_signoff_receipt_hash=final_hash,
            independent_verification_receipt_hash=independent_hash,
            transparency_root_hash=transparency_hash,
            policy_decision_receipt_hash=policy_hash,
            fault_simulation_report_hash=fault_hash,
            release_notes_digest=release_notes_digest,
            release_notes_relpath=_RELEASE_NOTES_RELPATH,
            tag_command_digest=tag_command_digest,
            tag_command_proposal=tag_command,
            tag_command_proposal_relpath=_TAG_COMMAND_RELPATH,
            tag_created=False,
            tag_pushed=False,
            external_artifacts_published=False,
            wal_record_hash=wal_record_hash,
            observed_at=observed,
        )
        self._persist_outputs(receipt, notes_text)
        return receipt

    def _required_upstreams(self, value: object) -> tuple[str, ...]:
        if value is None:
            keys = ["final_signoff_receipt"]
            for key, relpath in _OPTIONAL_UPSTREAM_FILES.items():
                if (self.repo_root / relpath).is_file():
                    keys.append(key)
            return tuple(keys)
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
            raise ReleaseCeremonyGateError("required_upstreams_must_be_sequence")
        normalized = tuple(str(item) for item in value)
        for key in normalized:
            if key not in _UPSTREAM_KEYS:
                raise ReleaseCeremonyGateError("required_upstream_unknown:" + key)
        if "final_signoff_receipt" not in normalized:
            raise ReleaseCeremonyGateError("final_signoff_receipt_required")
        return tuple(_dedupe(normalized))

    def _load_upstream_mapping(
        self,
        evidence: Mapping[str, object],
        key: str,
    ) -> Mapping[str, object] | None:
        value = evidence.get(key)
        if isinstance(value, Mapping):
            return _json_ready(value)  # type: ignore[return-value]
        relpath_value = evidence.get(key + "_relpath")
        if relpath_value is None:
            return None
        relpath = _string_value(relpath_value, key + "_relpath")
        path = self._resolve_relpath(relpath, key + "_relpath")
        if not path.is_file():
            raise ReleaseCeremonyGateError(key + "_relpath_missing")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ReleaseCeremonyGateError(key + "_relpath_invalid_json") from exc
        if not isinstance(payload, Mapping):
            raise ReleaseCeremonyGateError(key + "_relpath_must_be_json_object")
        return _json_ready(payload)  # type: ignore[return-value]

    def _read_current_head(self) -> object:
        git_head = self.repo_root / ".git" / "HEAD"
        if not git_head.is_file():
            return ZERO_HEAD
        text = git_head.read_text(encoding="utf-8").strip()
        if _HEAD_PATTERN.match(text):
            return text
        if not text.startswith("ref: "):
            return ZERO_HEAD
        ref = text[5:].strip()
        if "\\" in ref or ref.startswith("/") or ".." in PurePosixPath(ref).parts:
            return ZERO_HEAD
        ref_path = self.repo_root / ".git" / ref
        if ref_path.is_file():
            ref_text = ref_path.read_text(encoding="utf-8").strip()
            if _HEAD_PATTERN.match(ref_text):
                return ref_text
        packed_refs = self.repo_root / ".git" / "packed-refs"
        if packed_refs.is_file():
            for line in packed_refs.read_text(encoding="utf-8").splitlines():
                if line.startswith("#") or not line.strip():
                    continue
                parts = line.split(" ", 1)
                if len(parts) == 2 and parts[1] == ref and _HEAD_PATTERN.match(parts[0]):
                    return parts[0]
        return ZERO_HEAD

    def _append_wal(
        self,
        *,
        accepted: bool,
        release_id: str,
        release_tag: str,
        expected_head: str,
        current_head: str,
        release_notes_digest: str,
        tag_command_digest: str,
        upstream_hashes: Mapping[str, str],
        observed_at: str,
    ) -> str:
        wal_path = self._resolve_relpath(_WAL_RELPATH, "wal_relpath")
        wal_path.parent.mkdir(parents=True, exist_ok=True)
        upstream_bundle_hash = _sha256_json(upstream_hashes)
        material = {
            "accepted": accepted,
            "current_head": current_head,
            "expected_head": expected_head,
            "release_notes_digest": release_notes_digest,
            "release_tag": release_tag,
            "tag_command_digest": tag_command_digest,
            "upstream_bundle_hash": upstream_bundle_hash,
        }
        return FileBackedRealWalStorage(wal_path).append(
            record_type="SYSTEM_ACCEPTANCE_EVENT",
            task_id=_TASK_ID,
            run_id=release_id,
            payload_hash=_sha256_json(material),
            digest_bindings={
                "release_notes_digest": release_notes_digest,
                "tag_command_digest": tag_command_digest,
                "upstream_bundle_hash": upstream_bundle_hash,
            },
            created_at=observed_at,
        ).record_hash

    def _persist_outputs(
        self,
        receipt: ReleaseCeremonyReceipt,
        notes_text: str,
    ) -> None:
        self._write_new_text(_RELEASE_NOTES_RELPATH, notes_text)
        self._write_new_json(
            _TAG_COMMAND_RELPATH,
            {
                "command": receipt.tag_command_proposal,
                "command_digest": receipt.tag_command_digest,
                "proposal_only": True,
                "tag_created": False,
                "tag_pushed": False,
            },
        )
        self._write_new_json(
            _REPORT_RELPATH,
            {
                "accepted": receipt.accepted,
                "current_main_head": receipt.current_main_head,
                "expected_main_head": receipt.expected_main_head,
                "failures": receipt.failures,
                "receipt_hash": receipt.receipt_hash,
                "release_notes_digest": receipt.release_notes_digest,
                "release_notes_relpath": receipt.release_notes_relpath,
                "release_tag_proposal": receipt.release_tag_proposal,
                "tag_command_digest": receipt.tag_command_digest,
                "tag_command_proposal_relpath": receipt.tag_command_proposal_relpath,
                "tag_created": receipt.tag_created,
                "tag_pushed": receipt.tag_pushed,
                "external_artifacts_published": receipt.external_artifacts_published,
                "wal_record_hash": receipt.wal_record_hash,
            },
        )
        receipt_relpath = (
            _RECEIPT_DIR_RELPATH
            + "/"
            + receipt.receipt_hash.removeprefix("sha256:")
            + ".json"
        )
        self._write_new_json(receipt_relpath, receipt.as_dict())

    def _write_new_json(self, relpath: str, payload: object) -> None:
        self._write_new_text(
            relpath,
            json.dumps(
                _json_ready(payload),
                sort_keys=True,
                indent=2,
                ensure_ascii=True,
            )
            + "\n",
        )

    def _write_new_text(self, relpath: str, text: str) -> None:
        path = self._resolve_relpath(relpath, "output_relpath")
        if path.exists():
            raise ReleaseCeremonyGateError("output_already_exists")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _resolve_relpath(self, relpath: str, field_name: str) -> Path:
        if not isinstance(relpath, str) or not relpath:
            raise ReleaseCeremonyGateError(
                field_name + "_must_be_nonempty_string"
            )
        if "\\" in relpath:
            raise ReleaseCeremonyGateError(field_name + "_backslash_forbidden")
        pure = PurePosixPath(relpath)
        if pure.is_absolute() or ".." in pure.parts:
            raise ReleaseCeremonyGateError(
                field_name + "_must_stay_under_runtime_root"
            )
        path = (self.runtime_root / pure).resolve(strict=False)
        root = self.runtime_root.resolve()
        if path != root and root not in path.parents:
            raise ReleaseCeremonyGateError(field_name + "_escapes_runtime_root")
        return path


def compute_release_ceremony_receipt_hash(receipt: ReleaseCeremonyReceipt) -> str:
    return _sha256_json(receipt.deterministic_material())


def _verify_final_signoff(
    receipt: Mapping[str, object],
    release_tag: str,
) -> tuple[str, tuple[str, ...]]:
    failures: list[str] = []
    receipt_hash = _hash_field(receipt, "receipt_hash", failures)
    if receipt.get("integration_version") != _FINAL_SIGNOFF_VERSION:
        failures.append("final_signoff_receipt_version_invalid")
    if receipt.get("accepted") is not True:
        failures.append("final_signoff_receipt_not_accepted")
    if receipt.get("final_verdict") != _FINAL_VERDICT:
        failures.append("final_signoff_receipt_verdict_not_ready")
    if receipt.get("release_tag_proposal") != release_tag:
        failures.append("final_signoff_release_tag_mismatch")
    if not _HEAD_PATTERN.match(str(receipt.get("main_head", ""))):
        failures.append("final_signoff_main_head_invalid")
    return receipt_hash, tuple(_dedupe(failures))


def _verify_independent_verification(
    receipt: Mapping[str, object] | None,
) -> tuple[str, tuple[str, ...]]:
    if receipt is None:
        return ZERO_HASH, ()
    failures: list[str] = []
    receipt_hash = _hash_field(receipt, "receipt_hash", failures)
    if receipt.get("integration_version") != _INDEPENDENT_VERIFICATION_VERSION:
        failures.append("independent_verification_version_invalid")
    if receipt.get("accepted") is not True:
        failures.append("independent_verification_receipt_not_accepted")
    return receipt_hash, tuple(_dedupe(failures))


def _verify_transparency_root(
    receipt: Mapping[str, object] | None,
) -> tuple[str, tuple[str, ...]]:
    if receipt is None:
        return ZERO_HASH, ()
    failures: list[str] = []
    root_hash = _hash_field(receipt, "root_hash", failures)
    _hash_field(receipt, "receipt_hash", failures)
    if receipt.get("transparency_version") != _TRANSPARENCY_VERSION:
        failures.append("transparency_root_version_invalid")
    if receipt.get("accepted") is not True:
        failures.append("transparency_root_receipt_not_accepted")
    return root_hash, tuple(_dedupe(failures))


def _verify_policy_decision(
    receipt: Mapping[str, object] | None,
) -> tuple[str, tuple[str, ...]]:
    if receipt is None:
        return ZERO_HASH, ()
    failures: list[str] = []
    receipt_hash = _hash_field(receipt, "receipt_hash", failures)
    if receipt.get("decision_version") != _POLICY_VERSION:
        failures.append("policy_decision_version_invalid")
    if receipt.get("allowed") is not True or receipt.get("decision") != "allow":
        failures.append("policy_decision_not_allowed")
    return receipt_hash, tuple(_dedupe(failures))


def _verify_fault_simulation(
    report: Mapping[str, object] | None,
) -> tuple[str, tuple[str, ...]]:
    if report is None:
        return ZERO_HASH, ()
    failures: list[str] = []
    report_hash = _hash_field(report, "report_hash", failures)
    if report.get("simulation_version") != _FAULT_SIMULATION_VERSION:
        failures.append("fault_simulation_version_invalid")
    if report.get("accepted") is not True:
        failures.append("fault_simulation_report_not_accepted")
    results = report.get("fault_results", ())
    if not isinstance(results, Sequence) or isinstance(results, (str, bytes)) or not results:
        failures.append("fault_simulation_results_required")
    else:
        for index, result in enumerate(results, start=1):
            if not isinstance(result, Mapping):
                failures.append("fault_simulation_result_must_be_mapping:" + str(index))
                continue
            fault_id = str(result.get("fault_id", index))
            if result.get("detected") is not True:
                failures.append("fault_simulation_not_detected:" + fault_id)
            if result.get("safe_recovery") is not True:
                failures.append("fault_simulation_unsafe_recovery:" + fault_id)
    return report_hash, tuple(_dedupe(failures))


def _release_tag_failures(release_tag: str) -> tuple[str, ...]:
    if not _RELEASE_TAG_PATTERN.match(release_tag):
        return ("release_tag_proposal_invalid",)
    return ()


def _release_notes_text(
    *,
    release_id: str,
    release_tag: str,
    expected_head: str,
    observed_at: str,
    upstream_hashes: Mapping[str, str],
) -> str:
    lines = [
        "# Post-529 Release Ceremony Draft",
        "",
        f"Release ID: {release_id}",
        f"Tag proposal: {release_tag}",
        f"Expected main HEAD: {expected_head}",
        f"Observed at: {observed_at}",
        "",
        "This is a local draft artifact. No tag was created, no tag was pushed, and no external release artifact was published.",
        "",
        "Verified upstream evidence:",
    ]
    for key in sorted(upstream_hashes):
        lines.append(f"- {key}: {upstream_hashes[key]}")
    lines.append("")
    return "\n".join(lines)


def _tag_command_proposal(release_tag: str, expected_head: str) -> str:
    return (
        "git tag -a "
        + release_tag
        + " "
        + expected_head
        + ' -m "Release candidate '
        + release_tag
        + '"'
    )


def _hash_field(
    payload: Mapping[str, object],
    field_name: str,
    failures: list[str],
) -> str:
    value = payload.get(field_name)
    if not isinstance(value, str) or not _SHA256_PATTERN.match(value):
        failures.append(field_name + "_invalid")
        return ZERO_HASH
    return value


def _normalized_head(
    value: object,
    failures: list[str],
    field_name: str,
) -> str:
    if isinstance(value, str) and _HEAD_PATTERN.match(value):
        return value
    failures.append(field_name + "_invalid")
    return ZERO_HEAD


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
        raise ReleaseCeremonyGateError("value_must_be_json_serializable") from exc


def _sha256_json(value: object) -> str:
    encoded = json.dumps(
        _json_ready(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _require_nonempty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ReleaseCeremonyGateError(field_name + "_must_be_nonempty_string")


def _require_head(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not _HEAD_PATTERN.match(value):
        raise ReleaseCeremonyGateError(field_name + "_must_be_head_sha")


def _require_sha256(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not _SHA256_PATTERN.match(value):
        raise ReleaseCeremonyGateError(field_name + "_must_be_sha256")


def _string_field(data: Mapping[str, object], field_name: str, default: str) -> str:
    value = data.get(field_name, default)
    if not isinstance(value, str) or not value.strip():
        return default
    return value


def _string_value(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ReleaseCeremonyGateError(field_name + "_must_be_nonempty_string")
    return value


def _normalize_strings(values: Sequence[str], field_name: str) -> tuple[str, ...]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise ReleaseCeremonyGateError(field_name + "s_must_be_sequence")
    normalized = tuple(str(value) for value in values)
    for value in normalized:
        _require_nonempty_string(value, field_name)
    return tuple(_dedupe(normalized))


def _install_or_verify_hash(instance: object, field_name: str, compute) -> None:
    current = getattr(instance, field_name)
    expected = compute(instance)
    if current in ("", None):
        object.__setattr__(instance, field_name, expected)
        return
    if current != expected:
        raise ReleaseCeremonyGateError(field_name + "_mismatch")


def _dedupe(values: Sequence[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            output.append(value)
    return tuple(output)
