"""Capability token lifecycle for bounded local runner actions.

This module is a standalone contract implementation for local-runner
capability tokens. It does not execute commands, call providers, open
network/browser surfaces, persist credentials, or mutate files.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
import hashlib
import json

from kernel.runtime._strict_validation import strict_digest, strict_nonempty_string
from kernel.runtime.real_local_runner_boundary import (
    REAL_LOCAL_RUNNER_COMMAND_ALLOWLIST,
    REAL_LOCAL_RUNNER_EXECUTABLE_RESOLUTION_POLICY_ID,
)

__all__ = [
    "ALLOWED_LOCAL_RUNNER_COMMAND_IDS",
    "CapabilityToken",
    "CapabilityTokenLifecycle",
    "TokenLifecycleReceipt",
    "TokenLifecycleResult",
]

_POLICY_VERSION = "capability-token-lifecycle-v1"
_CODE_VERSION = "0.1.0"
REAL_LOCAL_RUNNER_BOUNDARY_POLICY_ID = "real_local_runner_boundary_v1"
CAPABILITY_TOKEN_SCOPE = "local_runner_validation"

ALLOWED_LOCAL_RUNNER_COMMAND_IDS: tuple[str, ...] = tuple(
    REAL_LOCAL_RUNNER_COMMAND_ALLOWLIST.keys()
)


@dataclass(frozen=True)
class CapabilityToken:
    """Authority descriptor bound to one local-runner command request."""

    token_id: str
    command_id: str
    scope: str
    run_id: str
    approval_artifact_id: str
    approval_artifact_digest: str
    repo_revision: str
    runner_policy_id: str
    executable_resolution_policy_id: str
    issued_at: str
    expires_at: str
    issue_nonce_digest: str
    single_use: bool = True
    consumed_at: str | None = None
    consumed_nonce_digest: str | None = None
    revoked_at: str | None = None
    revocation_reason: str | None = None
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION
    shell_authorized: bool = False
    arbitrary_argv_authorized: bool = False
    command_line_authorized: bool = False
    network_authorized: bool = False
    browser_authorized: bool = False
    provider_api_authorized: bool = False
    production_autonomy_authorized: bool = False
    production_admitted: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "arbitrary_argv_authorized": self.arbitrary_argv_authorized,
            "approval_artifact_digest": self.approval_artifact_digest,
            "approval_artifact_id": self.approval_artifact_id,
            "browser_authorized": self.browser_authorized,
            "code_version": self.code_version,
            "command_line_authorized": self.command_line_authorized,
            "command_id": self.command_id,
            "consumed_at": self.consumed_at,
            "consumed_nonce_digest": self.consumed_nonce_digest,
            "expires_at": self.expires_at,
            "executable_resolution_policy_id": (
                self.executable_resolution_policy_id
            ),
            "issue_nonce_digest": self.issue_nonce_digest,
            "issued_at": self.issued_at,
            "network_authorized": self.network_authorized,
            "policy_version": self.policy_version,
            "production_admitted": self.production_admitted,
            "production_autonomy_authorized": self.production_autonomy_authorized,
            "provider_api_authorized": self.provider_api_authorized,
            "repo_revision": self.repo_revision,
            "revocation_reason": self.revocation_reason,
            "revoked_at": self.revoked_at,
            "run_id": self.run_id,
            "runner_policy_id": self.runner_policy_id,
            "scope": self.scope,
            "shell_authorized": self.shell_authorized,
            "single_use": self.single_use,
            "token_id": self.token_id,
        }


@dataclass(frozen=True)
class TokenLifecycleReceipt:
    """Deterministic audit receipt for issue, consume, revoke, and reject."""

    event_type: str
    token_id: str
    accepted: bool
    failures: tuple[str, ...]
    command_id: str
    scope: str
    run_id: str
    approval_artifact_id: str
    approval_artifact_digest: str
    repo_revision: str
    runner_policy_id: str
    executable_resolution_policy_id: str
    receipt_hash: str
    observed_at: str
    policy_version: str = _POLICY_VERSION
    code_version: str = _CODE_VERSION

    def deterministic_material(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "approval_artifact_digest": self.approval_artifact_digest,
            "approval_artifact_id": self.approval_artifact_id,
            "code_version": self.code_version,
            "command_id": self.command_id,
            "event_type": self.event_type,
            "executable_resolution_policy_id": (
                self.executable_resolution_policy_id
            ),
            "failures": list(self.failures),
            "policy_version": self.policy_version,
            "repo_revision": self.repo_revision,
            "run_id": self.run_id,
            "runner_policy_id": self.runner_policy_id,
            "scope": self.scope,
            "token_id": self.token_id,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["arbitrary_argv_authorized"] = False
        payload["browser_authorized"] = False
        payload["command_line_authorized"] = False
        payload["network_authorized"] = False
        payload["observed_at"] = self.observed_at
        payload["production_admitted"] = False
        payload["production_autonomy_authorized"] = False
        payload["provider_api_authorized"] = False
        payload["receipt_hash"] = self.receipt_hash
        payload["shell_authorized"] = False
        return payload


@dataclass(frozen=True)
class TokenLifecycleResult:
    accepted: bool
    token: CapabilityToken | None
    receipt: TokenLifecycleReceipt


class CapabilityTokenLifecycle:
    """In-memory lifecycle state for local-runner capability tokens.

    The store is intentionally process-local and explicit. It grants no
    authority outside the caller's own use of the returned receipts.
    """

    def __init__(
        self,
        *,
        allowed_command_ids: tuple[str, ...] = ALLOWED_LOCAL_RUNNER_COMMAND_IDS,
    ) -> None:
        if not allowed_command_ids or not all(
            strict_nonempty_string(item) for item in allowed_command_ids
        ):
            raise ValueError("allowed_command_ids_must_be_nonempty_strings")
        self._allowed_command_ids = tuple(allowed_command_ids)
        self._tokens: dict[str, CapabilityToken] = {}
        self._issue_nonce_digests: set[str] = set()
        self._consume_nonce_digests: set[str] = set()

    @property
    def allowed_command_ids(self) -> tuple[str, ...]:
        return self._allowed_command_ids

    def issue(
        self,
        *,
        command_id: str,
        scope: str,
        run_id: str,
        approval_artifact_id: str,
        approval_artifact_digest: str,
        repo_revision: str,
        runner_policy_id: str = REAL_LOCAL_RUNNER_BOUNDARY_POLICY_ID,
        executable_resolution_policy_id: str = (
            REAL_LOCAL_RUNNER_EXECUTABLE_RESOLUTION_POLICY_ID
        ),
        expires_at: str,
        issue_nonce: str,
        issued_at: str | None = None,
        observed_at: str | None = None,
    ) -> TokenLifecycleResult:
        """Issue a single-use token for one approved local-runner command."""

        issued = _timestamp(issued_at)
        issue_nonce_digest = _digest_text(issue_nonce) if strict_nonempty_string(issue_nonce) else ""
        failures = _validate_common_binding(
            command_id=command_id,
            scope=scope,
            run_id=run_id,
            approval_artifact_id=approval_artifact_id,
            approval_artifact_digest=approval_artifact_digest,
            repo_revision=repo_revision,
            runner_policy_id=runner_policy_id,
            executable_resolution_policy_id=executable_resolution_policy_id,
            allowed_command_ids=self._allowed_command_ids,
        )
        if not strict_nonempty_string(issue_nonce):
            failures.append("issue_nonce_required")
        if issue_nonce_digest and issue_nonce_digest in self._issue_nonce_digests:
            failures.append("issue_nonce_replay")
        expiry = _parse_time(expires_at)
        if expiry is None:
            failures.append("expires_at_invalid")
        else:
            if expiry <= _parse_time(issued):
                failures.append("expires_at_must_be_after_issued_at")

        token_id = ""
        token: CapabilityToken | None = None
        if not failures:
            token_id = _token_id(
                command_id=command_id,
                scope=scope,
                approval_artifact_id=approval_artifact_id,
                approval_artifact_digest=approval_artifact_digest,
                repo_revision=repo_revision,
                run_id=run_id,
                runner_policy_id=runner_policy_id,
                executable_resolution_policy_id=executable_resolution_policy_id,
                issued_at=issued,
                expires_at=expires_at,
                issue_nonce_digest=issue_nonce_digest,
            )
            token = CapabilityToken(
                token_id=token_id,
                command_id=command_id,
                scope=scope,
                run_id=run_id,
                approval_artifact_id=approval_artifact_id,
                approval_artifact_digest=approval_artifact_digest,
                repo_revision=repo_revision,
                runner_policy_id=runner_policy_id,
                executable_resolution_policy_id=executable_resolution_policy_id,
                issued_at=issued,
                expires_at=expires_at,
                issue_nonce_digest=issue_nonce_digest,
            )
            self._tokens[token_id] = token
            self._issue_nonce_digests.add(issue_nonce_digest)

        receipt = _receipt(
            event_type="token_issued",
            token_id=token_id,
            accepted=not failures,
            failures=failures,
            command_id=command_id,
            scope=scope,
            run_id=run_id,
            approval_artifact_id=approval_artifact_id,
            approval_artifact_digest=approval_artifact_digest,
            repo_revision=repo_revision,
            runner_policy_id=runner_policy_id,
            executable_resolution_policy_id=executable_resolution_policy_id,
            observed_at=observed_at,
        )
        return TokenLifecycleResult(not failures, token, receipt)

    def consume(
        self,
        *,
        token_id: str,
        command_id: str,
        scope: str,
        run_id: str,
        approval_artifact_id: str,
        approval_artifact_digest: str,
        repo_revision: str,
        runner_policy_id: str = REAL_LOCAL_RUNNER_BOUNDARY_POLICY_ID,
        executable_resolution_policy_id: str = (
            REAL_LOCAL_RUNNER_EXECUTABLE_RESOLUTION_POLICY_ID
        ),
        consume_nonce: str,
        now: str | None = None,
        observed_at: str | None = None,
    ) -> TokenLifecycleResult:
        """Consume a token once, enforcing all bound request fields."""

        active_now = _timestamp(now)
        consume_nonce_digest = _digest_text(consume_nonce) if strict_nonempty_string(consume_nonce) else ""
        failures = _validate_common_binding(
            command_id=command_id,
            scope=scope,
            run_id=run_id,
            approval_artifact_id=approval_artifact_id,
            approval_artifact_digest=approval_artifact_digest,
            repo_revision=repo_revision,
            runner_policy_id=runner_policy_id,
            executable_resolution_policy_id=executable_resolution_policy_id,
            allowed_command_ids=self._allowed_command_ids,
        )
        if not strict_nonempty_string(token_id):
            failures.append("token_id_required")
        if not strict_nonempty_string(consume_nonce):
            failures.append("consume_nonce_required")
        if consume_nonce_digest and consume_nonce_digest in self._consume_nonce_digests:
            failures.append("replay_nonce_reused")

        token = self._tokens.get(token_id)
        if token is None:
            failures.append("unknown_token")
        else:
            _validate_token_matches_request(
                token,
                command_id=command_id,
                scope=scope,
                run_id=run_id,
                approval_artifact_id=approval_artifact_id,
                approval_artifact_digest=approval_artifact_digest,
                repo_revision=repo_revision,
                runner_policy_id=runner_policy_id,
                executable_resolution_policy_id=executable_resolution_policy_id,
                failures=failures,
            )
            expiry = _parse_time(token.expires_at)
            if expiry is None or expiry <= _parse_time(active_now):
                failures.append("token_expired")
            if token.revoked_at is not None:
                failures.append("token_revoked")
            if token.single_use and token.consumed_at is not None:
                failures.append("token_already_consumed")

        updated_token = token
        if token is not None and not failures:
            updated_token = replace(
                token,
                consumed_at=active_now,
                consumed_nonce_digest=consume_nonce_digest,
            )
            self._tokens[token_id] = updated_token
            self._consume_nonce_digests.add(consume_nonce_digest)

        receipt = _receipt(
            event_type="token_consumed",
            token_id=token_id,
            accepted=not failures,
            failures=failures,
            command_id=command_id,
            scope=scope,
            run_id=run_id,
            approval_artifact_id=approval_artifact_id,
            approval_artifact_digest=approval_artifact_digest,
            repo_revision=repo_revision,
            runner_policy_id=runner_policy_id,
            executable_resolution_policy_id=executable_resolution_policy_id,
            observed_at=observed_at,
        )
        return TokenLifecycleResult(not failures, updated_token if not failures else token, receipt)

    def revoke(
        self,
        *,
        token_id: str,
        reason: str,
        revoked_at: str | None = None,
        observed_at: str | None = None,
    ) -> TokenLifecycleResult:
        """Revoke an issued token without deleting its audit state."""

        failures: list[str] = []
        if not strict_nonempty_string(token_id):
            failures.append("token_id_required")
        if not strict_nonempty_string(reason):
            failures.append("revocation_reason_required")

        token = self._tokens.get(token_id)
        if token is None:
            failures.append("unknown_token")
            command_id = ""
            scope = ""
            approval_artifact_id = ""
            approval_artifact_digest = ""
            repo_revision = ""
        else:
            if token.revoked_at is not None:
                failures.append("token_already_revoked")
            command_id = token.command_id
            scope = token.scope
            run_id = token.run_id
            approval_artifact_id = token.approval_artifact_id
            approval_artifact_digest = token.approval_artifact_digest
            repo_revision = token.repo_revision
            runner_policy_id = token.runner_policy_id
            executable_resolution_policy_id = token.executable_resolution_policy_id
        if token is None:
            run_id = ""
            runner_policy_id = ""
            executable_resolution_policy_id = ""

        updated_token = token
        if token is not None and not failures:
            updated_token = replace(
                token,
                revoked_at=_timestamp(revoked_at),
                revocation_reason=reason,
            )
            self._tokens[token_id] = updated_token

        receipt = _receipt(
            event_type="token_revoked",
            token_id=token_id,
            accepted=not failures,
            failures=failures,
            command_id=command_id,
            scope=scope,
            run_id=run_id,
            approval_artifact_id=approval_artifact_id,
            approval_artifact_digest=approval_artifact_digest,
            repo_revision=repo_revision,
            runner_policy_id=runner_policy_id,
            executable_resolution_policy_id=executable_resolution_policy_id,
            observed_at=observed_at,
        )
        return TokenLifecycleResult(not failures, updated_token, receipt)

    def get(self, token_id: str) -> CapabilityToken | None:
        return self._tokens.get(token_id)


def _validate_common_binding(
    *,
    command_id: str,
    scope: str,
    run_id: str,
    approval_artifact_id: str,
    approval_artifact_digest: str,
    repo_revision: str,
    runner_policy_id: str,
    executable_resolution_policy_id: str,
    allowed_command_ids: tuple[str, ...],
) -> list[str]:
    failures: list[str] = []
    for field, value in (
        ("command_id", command_id),
        ("scope", scope),
        ("run_id", run_id),
        ("approval_artifact_id", approval_artifact_id),
        ("repo_revision", repo_revision),
        ("runner_policy_id", runner_policy_id),
        ("executable_resolution_policy_id", executable_resolution_policy_id),
    ):
        if not strict_nonempty_string(value):
            failures.append(f"{field}_required")
    if command_id and command_id not in allowed_command_ids:
        failures.append("command_id_not_allowlisted")
    if scope != CAPABILITY_TOKEN_SCOPE:
        failures.append("scope_not_allowed")
    if runner_policy_id != REAL_LOCAL_RUNNER_BOUNDARY_POLICY_ID:
        failures.append("runner_policy_id_mismatch")
    if executable_resolution_policy_id != REAL_LOCAL_RUNNER_EXECUTABLE_RESOLUTION_POLICY_ID:
        failures.append("executable_resolution_policy_id_mismatch")
    if not strict_digest(approval_artifact_digest):
        failures.append("approval_artifact_digest_required")
    return failures


def _validate_token_matches_request(
    token: CapabilityToken,
    *,
    command_id: str,
    scope: str,
    run_id: str,
    approval_artifact_id: str,
    approval_artifact_digest: str,
    repo_revision: str,
    runner_policy_id: str,
    executable_resolution_policy_id: str,
    failures: list[str],
) -> None:
    if token.command_id != command_id:
        failures.append("command_id_mismatch")
    if token.scope != scope:
        failures.append("scope_mismatch")
    if token.run_id != run_id:
        failures.append("run_id_mismatch")
    if token.approval_artifact_id != approval_artifact_id:
        failures.append("approval_artifact_id_mismatch")
    if token.approval_artifact_digest != approval_artifact_digest:
        failures.append("approval_artifact_digest_mismatch")
    if token.repo_revision != repo_revision:
        failures.append("repo_revision_mismatch")
    if token.runner_policy_id != runner_policy_id:
        failures.append("runner_policy_id_mismatch")
    if token.executable_resolution_policy_id != executable_resolution_policy_id:
        failures.append("executable_resolution_policy_id_mismatch")


def _timestamp(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if not strict_nonempty_string(value):
        raise ValueError("timestamp_must_be_nonempty_string")
    if _parse_time(value) is None:
        raise ValueError("timestamp_must_be_isoformat")
    return value


def _parse_time(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _token_id(
    *,
    command_id: str,
    scope: str,
    approval_artifact_id: str,
    approval_artifact_digest: str,
    repo_revision: str,
    run_id: str,
    runner_policy_id: str,
    executable_resolution_policy_id: str,
    issued_at: str,
    expires_at: str,
    issue_nonce_digest: str,
) -> str:
    payload = {
        "approval_artifact_digest": approval_artifact_digest,
        "approval_artifact_id": approval_artifact_id,
        "command_id": command_id,
        "expires_at": expires_at,
        "executable_resolution_policy_id": executable_resolution_policy_id,
        "issue_nonce_digest": issue_nonce_digest,
        "issued_at": issued_at,
        "repo_revision": repo_revision,
        "run_id": run_id,
        "runner_policy_id": runner_policy_id,
        "scope": scope,
    }
    return "cap_local_runner_" + _digest_payload(payload).split(":", 1)[1][:32]


def _receipt(
    *,
    event_type: str,
    token_id: str,
    accepted: bool,
    failures: list[str],
    command_id: str,
    scope: str,
    run_id: str,
    approval_artifact_id: str,
    approval_artifact_digest: str,
    repo_revision: str,
    runner_policy_id: str,
    executable_resolution_policy_id: str,
    observed_at: str | None,
) -> TokenLifecycleReceipt:
    normalized_failures = tuple(sorted(set(failures)))
    material = {
        "accepted": accepted,
        "approval_artifact_digest": approval_artifact_digest,
        "approval_artifact_id": approval_artifact_id,
        "code_version": _CODE_VERSION,
        "command_id": command_id,
        "event_type": event_type,
        "executable_resolution_policy_id": executable_resolution_policy_id,
        "failures": list(normalized_failures),
        "policy_version": _POLICY_VERSION,
        "repo_revision": repo_revision,
        "run_id": run_id,
        "runner_policy_id": runner_policy_id,
        "scope": scope,
        "token_id": token_id,
    }
    return TokenLifecycleReceipt(
        event_type=event_type,
        token_id=token_id,
        accepted=accepted,
        failures=normalized_failures,
        command_id=command_id,
        scope=scope,
        run_id=run_id,
        approval_artifact_id=approval_artifact_id,
        approval_artifact_digest=approval_artifact_digest,
        repo_revision=repo_revision,
        runner_policy_id=runner_policy_id,
        executable_resolution_policy_id=executable_resolution_policy_id,
        receipt_hash=_digest_payload(material),
        observed_at=_timestamp(observed_at),
    )


def _digest_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _digest_payload(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()
