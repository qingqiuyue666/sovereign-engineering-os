"""
Real-fix tracer: one real provider-backed model invocation that produces
a verifiable single-file code fix.

Constitutional anchors:
- v11 §22.9 (inter-plane interface discipline; the adapter boundary is
  the only admissible real-model entry point).
- v11 §23.5 InferenceArtifact — this tracer does NOT persist an
  InferenceArtifact because it is an out-of-band ignition probe, not a
  signable-path invocation. It emits audit-only evidence.
- v11 §23.15 FailureBundle linkage — adapter-normalized failures are
  surfaced as explicit ``real_fix_adapter_failure`` audit records that
  carry the adapter's failure class tag.
- governance/design/replay_claim_taxonomy/02_claim_class_definitions.md §3
  — ``semantic`` is the honest replay ceiling for real-provider output.
  Every audit record emitted by this tracer carries
  ``replay_ceiling == "semantic"``.

Scope lock (this is a tracer, not a feature):
- ONE minimal, deterministic, single-file fix task at a time. A task is
  a ``RealFixTask`` carrying (broken_source, instruction, function_name,
  verification_cases). Anything else is out of scope.
- ONE real adapter. The tracer accepts a ``ModelAdapter`` with the same
  shape as ``kernel.services.inference_service.ModelAdapter`` and the
  concrete production adapter is
  ``kernel.adapters.anthropic_adapter.AnthropicMessagesAdapter``.
- NO retries. The adapter's policy carries ``max_retries = 0`` and this
  tracer issues exactly one invocation.
- NO silent downgrade. Every failure mode returns an explicit
  ``RealFixResult(verified=False, ...)`` and emits an audit record that
  names the failure class.
- NO claim of exact replay. The ``replay_ceiling`` recorded on every
  audit record is ``"semantic"``.

Outcome classes (exactly one per tracer run):
- ``real_fix_verified_pass``       all verification cases pass
- ``real_fix_verified_fail``       at least one verification case fails
- ``real_fix_unparseable``         response has no fenced Python block
- ``real_fix_exec_error``          extracted source raises at exec/call
- ``real_fix_adapter_failure``     adapter raised ``InferenceFailure``
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence, Tuple

from kernel.services.inference_service import InferenceFailure, InferencePolicy


# ---------------------------------------------------------------------------
# Tracer data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RealFixTask:
    """A single-file, single-function deterministic fix task.

    Fields:
    - ``task_id``             caller-chosen identifier, included in audit
    - ``broken_source``       the full text of the single file to repair
    - ``instruction``         a one-line human instruction for the model
    - ``function_name``       the module-scope function the caller will
                              call during verification
    - ``verification_cases``  sequence of (args, expected) tuples. On
                              verification the tracer calls the extracted
                              function with ``*args`` and compares the
                              return value to ``expected`` via ``==``.
                              All cases must pass for ``verified=True``.
    """

    task_id: str
    broken_source: str
    instruction: str
    function_name: str
    verification_cases: Sequence[Tuple[Tuple[Any, ...], Any]]


@dataclass(frozen=True)
class RealFixResult:
    """Outcome of one tracer invocation.

    ``verified == True`` iff the extracted source executed and every
    verification case matched. Any other outcome has ``verified = False``
    and ``outcome`` names the specific failure class.
    """

    verified: bool
    outcome: str  # one of the outcome classes declared in the module docstring
    fixed_source: str = ""
    output_hash: str = ""
    failure_class: str = ""
    failure_detail: str = ""
    latency_ms: int = 0
    replay_ceiling: str = "semantic"
    first_failing_case_index: int = -1
    extra: Mapping[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Extraction and verification helpers
# ---------------------------------------------------------------------------


# The model is instructed to emit exactly one fenced Python code block.
# We accept ```python ... ``` and (defensively) a bare ``` ... ``` block.
# Anything else is ``real_fix_unparseable``.
_FENCED_PYTHON_RE = re.compile(
    r"```(?:python|py)?\s*\n(?P<body>.*?)\n```",
    re.DOTALL | re.IGNORECASE,
)


def _extract_fixed_source(output_text: str) -> str | None:
    """Return the contents of the first fenced Python block, or None."""
    if not isinstance(output_text, str) or not output_text:
        return None
    m = _FENCED_PYTHON_RE.search(output_text)
    if m is None:
        return None
    body = m.group("body")
    if not isinstance(body, str) or not body.strip():
        return None
    return body


def _output_hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


# A deliberately narrow allowlist of builtins made available to the
# executed fixed source. The verification target is a pure-arithmetic
# function; we do not need file or network access. Any attempt by the
# executed source to reach outside this namespace will raise NameError,
# which is caught as ``real_fix_exec_error``.
_SAFE_BUILTINS: Mapping[str, Any] = {
    "abs": abs,
    "min": min,
    "max": max,
    "sum": sum,
    "len": len,
    "range": range,
    "int": int,
    "float": float,
    "bool": bool,
    "str": str,
    "tuple": tuple,
    "list": list,
    "dict": dict,
    "True": True,
    "False": False,
    "None": None,
}


def _exec_and_call(
    *,
    fixed_source: str,
    function_name: str,
    args: Tuple[Any, ...],
) -> Any:
    """Exec ``fixed_source`` in a restricted namespace and call ``function_name``.

    Raises any exception that exec or the call produces. Callers wrap
    this to translate those into ``real_fix_exec_error`` outcomes.
    """
    ns: dict[str, Any] = {"__builtins__": dict(_SAFE_BUILTINS)}
    exec(compile(fixed_source, "<real_fix_tracer>", "exec"), ns, ns)  # noqa: S102
    fn = ns.get(function_name)
    if not callable(fn):
        raise RuntimeError(
            f"fixed source does not define a callable `{function_name}`"
        )
    return fn(*args)


# ---------------------------------------------------------------------------
# Tracer
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class RealFixTracer:
    """Run one real-model fix invocation under the governed adapter boundary.

    The tracer does NOT mutate the signable-path ledger. It emits audit
    records only, via the supplied ``audit_ledger``. The audit records
    carry the honest replay ceiling.
    """

    def __init__(
        self,
        *,
        adapter: Any,
        audit_ledger: Any,
        policy: InferencePolicy | None = None,
    ) -> None:
        self._adapter = adapter
        self._audit = audit_ledger
        self._policy = policy or InferencePolicy(
            max_output_tokens=1024,
            timeout_seconds=60.0,
            max_retries=0,
        )

    # ------------------------------------------------------------------

    def _replay_ceiling(self) -> str:
        # Honest upper bound: whatever the adapter declares, else the
        # conservative default. Real-provider adapters declare
        # ``"semantic"``.
        ceiling = getattr(self._adapter, "replay_ceiling", None)
        if isinstance(ceiling, str) and ceiling:
            return ceiling
        return "semantic"

    def _build_envelope(self, task: RealFixTask) -> Mapping[str, Any]:
        """Build the governed prompt envelope the adapter consumes.

        The envelope is typed and carries every governed field the
        adapter's ``_build_request_body`` names. The ``fix_task`` key
        triggers the adapter's fix-task prompt mode.
        """
        return {
            "context_artifact_id": f"real-fix::{task.task_id}",
            "root_revision_id": f"real-fix::{task.task_id}",
            "candidate_file_ids": [f"real-fix::{task.function_name}.py"],
            "symbol_frontier_ids": [task.function_name],
            "content_hash": _output_hash(task.broken_source),
            "packing_policy_version": "real_fix_tracer_v1",
            "taint_set": [],
            "phase": "phase1",
            "fix_task": {
                "broken_source": task.broken_source,
                "instruction": task.instruction,
                "function_name": task.function_name,
                "language": "python",
            },
        }

    def _emit(
        self,
        *,
        record_type: str,
        task_id: str,
        payload: Mapping[str, Any],
    ) -> None:
        # Every real-model audit record carries the honest replay ceiling.
        full_payload = dict(payload)
        full_payload.setdefault("replay_ceiling", self._replay_ceiling())
        self._audit.append(
            record_type=record_type,
            task_id=task_id,
            artifact_refs=[f"real-fix::{task_id}"],
            payload=full_payload,
        )

    # ------------------------------------------------------------------

    def run(self, task: RealFixTask) -> RealFixResult:
        """Invoke the adapter once, verify, and emit evidence.

        Returns a ``RealFixResult``. Always returns; never silently
        downgrades. Adapter failures are normalized to
        ``real_fix_adapter_failure`` with the class tag preserved.
        """
        envelope = self._build_envelope(task)

        # Tracer start is recorded so the audit chain has a causally
        # prior record even if the adapter raises immediately.
        self._emit(
            record_type="real_fix_attempt_started",
            task_id=task.task_id,
            payload={
                "function_name": task.function_name,
                "instruction": task.instruction,
                "broken_source_hash": _output_hash(task.broken_source),
                "policy": {
                    "max_output_tokens": self._policy.max_output_tokens,
                    "timeout_seconds": self._policy.timeout_seconds,
                    "max_retries": self._policy.max_retries,
                },
            },
        )

        # Adapter boundary — the one real provider call.
        try:
            raw = self._adapter.invoke(
                prompt_envelope=envelope, policy=self._policy
            )
        except InferenceFailure as exc:
            detail = str(exc)
            failure_class = detail.split(":", 1)[0].strip() if ":" in detail else detail
            self._emit(
                record_type="real_fix_adapter_failure",
                task_id=task.task_id,
                payload={
                    "failure_class": failure_class or "unknown",
                    "detail": detail,
                },
            )
            return RealFixResult(
                verified=False,
                outcome="real_fix_adapter_failure",
                failure_class=failure_class or "unknown",
                failure_detail=detail,
                replay_ceiling=self._replay_ceiling(),
            )

        output_text = ""
        latency_ms = 0
        if isinstance(raw, Mapping):
            ot = raw.get("output_text")
            if isinstance(ot, str):
                output_text = ot
            lm = raw.get("latency_ms")
            if isinstance(lm, int):
                latency_ms = lm

        # Extract the fenced Python block.
        fixed = _extract_fixed_source(output_text)
        if fixed is None:
            self._emit(
                record_type="real_fix_unparseable",
                task_id=task.task_id,
                payload={
                    "detail": "no fenced python block in output_text",
                    "output_hash": _output_hash(output_text),
                    "latency_ms": latency_ms,
                },
            )
            return RealFixResult(
                verified=False,
                outcome="real_fix_unparseable",
                output_hash=_output_hash(output_text),
                latency_ms=latency_ms,
                replay_ceiling=self._replay_ceiling(),
            )

        fixed_hash = _output_hash(fixed)

        # Run verification cases. Any exec/call error is an exec failure.
        for idx, (args, expected) in enumerate(task.verification_cases):
            try:
                actual = _exec_and_call(
                    fixed_source=fixed,
                    function_name=task.function_name,
                    args=tuple(args),
                )
            except Exception as exc:  # noqa: BLE001 — fail-closed on any exec error
                self._emit(
                    record_type="real_fix_exec_error",
                    task_id=task.task_id,
                    payload={
                        "error_class": type(exc).__name__,
                        "detail": str(exc),
                        "output_hash": fixed_hash,
                        "case_index": idx,
                        "latency_ms": latency_ms,
                    },
                )
                return RealFixResult(
                    verified=False,
                    outcome="real_fix_exec_error",
                    fixed_source=fixed,
                    output_hash=fixed_hash,
                    failure_class=type(exc).__name__,
                    failure_detail=str(exc),
                    latency_ms=latency_ms,
                    first_failing_case_index=idx,
                    replay_ceiling=self._replay_ceiling(),
                )
            if actual != expected:
                self._emit(
                    record_type="real_fix_verified_fail",
                    task_id=task.task_id,
                    payload={
                        "case_index": idx,
                        "args": list(args),
                        "expected": expected,
                        "actual": actual,
                        "output_hash": fixed_hash,
                        "latency_ms": latency_ms,
                    },
                )
                return RealFixResult(
                    verified=False,
                    outcome="real_fix_verified_fail",
                    fixed_source=fixed,
                    output_hash=fixed_hash,
                    failure_class="verification_failed",
                    failure_detail=(
                        f"case {idx}: {task.function_name}{tuple(args)} "
                        f"returned {actual!r}, expected {expected!r}"
                    ),
                    latency_ms=latency_ms,
                    first_failing_case_index=idx,
                    replay_ceiling=self._replay_ceiling(),
                )

        # All cases passed.
        self._emit(
            record_type="real_fix_verified_pass",
            task_id=task.task_id,
            payload={
                "function_name": task.function_name,
                "output_hash": fixed_hash,
                "cases_passed": len(task.verification_cases),
                "latency_ms": latency_ms,
                "completed_at": _now_iso(),
            },
        )
        return RealFixResult(
            verified=True,
            outcome="real_fix_verified_pass",
            fixed_source=fixed,
            output_hash=fixed_hash,
            latency_ms=latency_ms,
            replay_ceiling=self._replay_ceiling(),
        )


# ---------------------------------------------------------------------------
# Canonical minimal task fixture
# ---------------------------------------------------------------------------


BROKEN_ADD_SOURCE = "def add(a, b):\n    return a - b\n"
"""The canonical broken single-file source: subtraction instead of addition."""


def make_add_fix_task(task_id: str) -> RealFixTask:
    """Return the canonical ``add`` fix task used by the phase-1 tracer.

    Reviewable by inspection: a single two-line function with a single
    wrong operator, four deterministic arithmetic verification cases.
    """
    return RealFixTask(
        task_id=task_id,
        broken_source=BROKEN_ADD_SOURCE,
        instruction=(
            "The function `add(a, b)` must return the sum `a + b`, not "
            "the difference. Fix the operator."
        ),
        function_name="add",
        verification_cases=(
            ((2, 3), 5),
            ((-1, 1), 0),
            ((0, 0), 0),
            ((10, -7), 3),
        ),
    )
