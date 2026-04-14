"""
Real-model adapter: Anthropic Messages API.

Constitutional anchors:
- v11 §22.9 (inter-plane interface discipline)
- v11 §23.5 InferenceArtifact
- v11 §23.15 FailureBundle linkage on API failure
- foundation §4.2 ModelIntegrationContract
- governance/design/replay_claim_taxonomy/02_claim_class_definitions.md §3
  (`semantic` is the honest default for non-host-deterministic producers)

Scope lock (phase-1 real-model ignition tracer):
- This module is the FIRST and ONLY real adapter wired into the narrow
  signable path. It exists to prove that the existing governed boundary
  (`kernel.services.inference_service.InferenceService`) accepts real
  provider output without broadening scope, silently downgrading
  evidence, or claiming replay fidelity that is not defensible.
- No retries. `InferencePolicy.max_retries = 0` is respected. Failure
  is explicit and fail-closed.
- No streaming. Phase-1 admits a single, typed response. Streaming is
  out of scope.
- No multi-provider fallback. If this adapter fails, `InferenceFailure`
  is raised and the service emits a failure bundle.
- No external SDK dependency. The adapter uses stdlib `urllib.request`.
  A caller MAY inject a custom transport (`transport` constructor arg)
  for tests; the default is `_default_transport` which speaks HTTPS.

Replay-claim posture (IMPORTANT):
- `AnthropicMessagesAdapter.replay_ceiling == "semantic"`.
- Provider output is NOT host-deterministic. We do not claim byte-exact
  replay for real-model artifacts. The inference service records this
  ceiling in the `inference_artifact_created` audit payload so that
  downstream replay anchors are minted honestly.
- Phase-1 replay classifier continues to refuse equivalence-proof
  bundles (INV-011). This adapter changes nothing there.

Normalized failure classes (all raised as `InferenceFailure` so the
service's existing `_emit_failure_bundle` path records them as
`model_api_failure` with the class tag in the detail string):
- `timeout`           socket/read timeout >= policy.timeout_seconds
- `network_error`     DNS / connection reset / SSL / other socket error
- `quota_exhausted`   HTTP 429 or error.type in {rate_limit_error, overloaded_error}
- `auth_error`        HTTP 401 or 403 (missing/invalid key, permission denied)
- `server_error`      HTTP 5xx
- `malformed_response`non-JSON body, missing required fields, or no text content
- `refusal`           stop_reason == "refusal" or policy-inadmissible empty content

Typed response contract (matches InferenceService._parse_response):
- output_text    str     concatenated text of the assistant message
- token_usage    dict    {"input": int, "output": int}
- latency_ms     int     wall-clock ms across the HTTPS round trip
- model_route_id str     the model id the provider actually served

The adapter does NOT produce any other shape. Anything else is an error.
"""

from __future__ import annotations

import json
import os
import socket
import ssl
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Mapping, Optional

from kernel.services.inference_service import InferenceFailure, InferencePolicy


# ---------------------------------------------------------------------------
# Constants (narrow; no policy expansion)
# ---------------------------------------------------------------------------

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"
DEFAULT_MODEL_ROUTE_ID = "claude-sonnet-4-5"

# Replay ceiling for real provider outputs. See module docstring.
REPLAY_CEILING = "semantic"


# ---------------------------------------------------------------------------
# Transport abstraction (so tests do not hit the network)
# ---------------------------------------------------------------------------


class _TransportResponse:
    """A minimal response shape the adapter consumes.

    Fields:
    - status: int HTTP status code
    - body: bytes response body (may be empty)
    """

    __slots__ = ("status", "body")

    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self.body = body


Transport = Callable[[str, bytes, Mapping[str, str], float], _TransportResponse]
"""A transport is a callable(url, body, headers, timeout_seconds) -> _TransportResponse.

It MUST raise one of:
- TimeoutError / socket.timeout        -> normalized to `timeout`
- urllib.error.URLError (or OSError)   -> normalized to `network_error`
Any other exception is normalized to `network_error` with the type name.
"""


def _default_transport(
    url: str,
    body: bytes,
    headers: Mapping[str, str],
    timeout_seconds: float,
) -> _TransportResponse:
    """Default stdlib HTTPS transport. Injectable for tests."""
    req = urllib.request.Request(url, data=body, method="POST")
    for k, v in headers.items():
        req.add_header(k, v)
    # urlopen raises HTTPError for 4xx/5xx — we want the body for error
    # parsing, so we catch and return a _TransportResponse in those cases.
    try:
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(
            req, timeout=timeout_seconds, context=ctx
        ) as resp:
            return _TransportResponse(status=resp.status, body=resp.read())
    except urllib.error.HTTPError as e:
        try:
            raw = e.read() or b""
        except Exception:  # noqa: BLE001
            raw = b""
        return _TransportResponse(status=e.code, body=raw)


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class AnthropicMessagesAdapter:
    """Anthropic Messages API adapter (phase-1 real-model ignition tracer).

    Construction:
    - api_key:   provider credential. Required. If `None`, the adapter
                 reads `ANTHROPIC_API_KEY`. If neither is set, calling
                 `invoke` raises InferenceFailure("auth_error: ...").
                 We do NOT fail at construction time; failure is visible
                 at the governed boundary, fail-closed.
    - model_route_id: model id to request. Default is DEFAULT_MODEL_ROUTE_ID.
    - transport: injectable transport callable (see Transport). Default
                 is the stdlib HTTPS transport.

    Instance attributes:
    - replay_ceiling: str  — `"semantic"`. The inference service reads
      this (if present) and records it on the audit payload.
    """

    # Declared ceiling. Classifiers / evidence consumers can treat this as
    # the honest upper bound for replay claims against artifacts produced
    # by this adapter.
    replay_ceiling: str = REPLAY_CEILING

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        model_route_id: str = DEFAULT_MODEL_ROUTE_ID,
        transport: Optional[Transport] = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else os.environ.get(
            "ANTHROPIC_API_KEY"
        )
        self._model_route_id = model_route_id
        self._transport: Transport = transport or _default_transport

    # ------------------------------------------------------------------
    # request construction
    # ------------------------------------------------------------------

    def _build_request_body(
        self,
        *,
        prompt_envelope: Mapping[str, Any],
        policy: InferencePolicy,
    ) -> bytes:
        """Build the Messages API request body from the governed envelope.

        The envelope is the typed prompt shape produced by
        `InferenceService._build_prompt_envelope`. We convert it to a
        deterministic JSON string that names every governed input
        (context_artifact_id, root_revision_id, packing_policy_version,
        candidate_file_ids, symbol_frontier_ids, taint_set). The model
        is told this is a phase-1 ignition tracer and asked to
        acknowledge. This keeps the real-model surface minimal and
        auditable.
        """
        # Deterministic serialization of the governed envelope so the
        # prompt content is a function of the envelope only.
        envelope_json = json.dumps(
            dict(prompt_envelope), sort_keys=True, separators=(",", ":")
        )
        user_content = (
            "Phase-1 ignition tracer. Governed prompt envelope follows.\n"
            "Acknowledge receipt and summarize the envelope in one sentence.\n"
            "Envelope:\n" + envelope_json
        )
        payload = {
            "model": self._model_route_id,
            "max_tokens": int(policy.max_output_tokens),
            "messages": [
                {"role": "user", "content": user_content},
            ],
        }
        return json.dumps(payload).encode("utf-8")

    # ------------------------------------------------------------------
    # response parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_output_text(content_blocks: Any) -> str:
        """Concatenate text from Messages API content blocks.

        Messages API returns `content: [{"type": "text", "text": "..."}, ...]`.
        Unknown block types are ignored; non-list content is rejected.
        """
        if not isinstance(content_blocks, list):
            raise InferenceFailure(
                "malformed_response: content is not a list"
            )
        parts: list[str] = []
        for blk in content_blocks:
            if not isinstance(blk, Mapping):
                continue
            if blk.get("type") == "text" and isinstance(blk.get("text"), str):
                parts.append(blk["text"])
        return "".join(parts)

    @staticmethod
    def _classify_http_error(status: int, body_obj: Any) -> str:
        """Map a non-2xx HTTP response to a normalized failure class.

        body_obj may be a parsed JSON dict (Anthropic error envelope) or
        None if parse failed.
        """
        err_type: Optional[str] = None
        if isinstance(body_obj, Mapping):
            err = body_obj.get("error")
            if isinstance(err, Mapping):
                et = err.get("type")
                if isinstance(et, str):
                    err_type = et

        if status == 429 or err_type in {"rate_limit_error", "overloaded_error"}:
            return "quota_exhausted"
        if status in (401, 403) or err_type in {
            "authentication_error",
            "permission_error",
        }:
            return "auth_error"
        if 500 <= status < 600 or err_type == "api_error":
            return "server_error"
        # 4xx that isn't auth/quota — treat as malformed request surface.
        return "malformed_response"

    # ------------------------------------------------------------------
    # governed entry point
    # ------------------------------------------------------------------

    def invoke(
        self,
        *,
        prompt_envelope: Mapping[str, Any],
        policy: InferencePolicy,
    ) -> Mapping[str, Any]:
        """Invoke the Anthropic Messages API under the governed policy.

        Returns a typed response dict:
            {"output_text", "token_usage", "latency_ms", "model_route_id"}

        Raises `InferenceFailure("<class>: <detail>")` on every normalized
        failure class.  The inference service's existing failure path
        writes the failure bundle.
        """
        if not self._api_key:
            raise InferenceFailure(
                "auth_error: ANTHROPIC_API_KEY is not set"
            )

        body = self._build_request_body(
            prompt_envelope=prompt_envelope, policy=policy
        )
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": ANTHROPIC_API_VERSION,
            "content-type": "application/json",
        }

        start = time.monotonic()
        try:
            resp = self._transport(
                ANTHROPIC_API_URL,
                body,
                headers,
                float(policy.timeout_seconds),
            )
        except (TimeoutError, socket.timeout) as e:
            raise InferenceFailure(f"timeout: {e}") from e
        except (urllib.error.URLError, OSError) as e:
            # URLError wraps socket.timeout on some Python versions; check.
            reason = getattr(e, "reason", e)
            if isinstance(reason, (TimeoutError, socket.timeout)):
                raise InferenceFailure(f"timeout: {reason}") from e
            raise InferenceFailure(f"network_error: {e}") from e
        except InferenceFailure:
            raise
        except Exception as e:  # noqa: BLE001 — fail-closed on unknown transport error
            raise InferenceFailure(
                f"network_error: {type(e).__name__}: {e}"
            ) from e

        latency_ms = int((time.monotonic() - start) * 1000)

        # Body must be valid JSON. Anything else is malformed.
        try:
            parsed: Any = json.loads(resp.body.decode("utf-8")) if resp.body else None
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise InferenceFailure(
                f"malformed_response: body is not valid JSON: {e}"
            ) from e

        if resp.status < 200 or resp.status >= 300:
            cls = self._classify_http_error(resp.status, parsed)
            detail = f"http {resp.status}"
            if isinstance(parsed, Mapping):
                err = parsed.get("error")
                if isinstance(err, Mapping):
                    msg = err.get("message")
                    if isinstance(msg, str):
                        detail = f"http {resp.status}: {msg}"
            raise InferenceFailure(f"{cls}: {detail}")

        if not isinstance(parsed, Mapping):
            raise InferenceFailure(
                "malformed_response: response body is not a JSON object"
            )

        content = parsed.get("content")
        output_text = self._extract_output_text(content)
        stop_reason = parsed.get("stop_reason")

        # Refusal semantics. Anthropic may emit an explicit `refusal`
        # stop_reason, or may return an empty content list with a
        # non-end_turn stop reason. Both are refusals as far as the
        # governed boundary is concerned.
        if stop_reason == "refusal":
            raise InferenceFailure(
                "refusal: provider returned stop_reason=refusal"
            )
        if not output_text:
            raise InferenceFailure(
                f"refusal: provider returned empty output "
                f"(stop_reason={stop_reason!r})"
            )

        usage = parsed.get("usage")
        if not isinstance(usage, Mapping):
            raise InferenceFailure(
                "malformed_response: usage field missing or not an object"
            )
        try:
            token_usage = {
                "input": int(usage.get("input_tokens", 0)),
                "output": int(usage.get("output_tokens", 0)),
            }
        except (TypeError, ValueError) as e:
            raise InferenceFailure(
                f"malformed_response: usage counts not integers: {e}"
            ) from e

        served_model = parsed.get("model")
        if not isinstance(served_model, str) or not served_model:
            served_model = self._model_route_id

        return {
            "output_text": output_text,
            "token_usage": token_usage,
            "latency_ms": latency_ms,
            "model_route_id": served_model,
        }
