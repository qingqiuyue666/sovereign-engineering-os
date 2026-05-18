"""Replay security — security boundary enforcement for replay engine.

No network. No subprocess. No cloud AI. No live provider.
No secret material. No raw payload in receipts.
No evidence mutation.
"""

from __future__ import annotations

from typing import Any, Dict, List


FORBIDDEN_IMPORTS = frozenset({
    "subprocess", "socket", "requests", "urllib", "http.client",
    "anthropic", "openai", "google.cloud",
})

FORBIDDEN_PATTERNS = (
    "API_KEY", "SECRET", "TOKEN", ".env", "password", "credential",
    "private_key", "raw_secret",
)

FORBIDDEN_ACTIONS = frozenset({
    "cloud_requery", "network_call", "live_execution", "provider_call",
    "trading", "production_deploy", "evidence_mutation",
    "branch_delete", "main_mutation", "push", "merge",
})


class ReplaySecurity:
    """Security boundary enforcement for replay engine runtime."""

    @staticmethod
    def validate_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            raise TypeError("payload must be a mapping")

        violations: List[str] = []

        for key, value in payload.items():
            key_upper = str(key).upper()
            for pattern in FORBIDDEN_PATTERNS:
                if pattern in key_upper:
                    violations.append(f"forbidden_key_pattern: {key}")
            if isinstance(value, str):
                for pattern in FORBIDDEN_PATTERNS:
                    if pattern.lower() in value.lower():
                        violations.append(f"forbidden_value_pattern_in_{key}")

        flags = payload.get("flags", [])
        if isinstance(flags, list):
            for flag in flags:
                if flag in FORBIDDEN_ACTIONS:
                    violations.append(f"forbidden_flag: {flag}")

        return {
            "valid": len(violations) == 0,
            "violations": violations,
        }

    @staticmethod
    def validate_no_network(payload: Dict[str, Any]) -> bool:
        text = str(payload).lower()
        network_patterns = ("curl", "wget", "ssh", "scp", "nc ", "telnet",
                           "socket", "http", "https://")
        return not any(p in text for p in network_patterns)

    @staticmethod
    def validate_no_secrets(payload: Dict[str, Any]) -> bool:
        text = str(payload).lower()
        secret_patterns = (".env", "api_key", "secret", "token", "password",
                          "credential", "private_key")
        return not any(p in text for p in secret_patterns)

    @staticmethod
    def validate_no_raw_payload(receipt: Dict[str, Any]) -> bool:
        forbidden_receipt_keys = {"raw_payload", "payload", "raw_data", "raw_input"}
        return not bool(forbidden_receipt_keys & set(receipt.keys()))

    @staticmethod
    def security_gates() -> Dict[str, bool]:
        return {
            "no_network": True,
            "no_cloud_ai": True,
            "no_live_provider": True,
            "no_secret_material": True,
            "no_evidence_mutation": True,
            "no_raw_payload_in_receipts": True,
            "deterministic_only": True,
            "fail_closed": True,
        }
