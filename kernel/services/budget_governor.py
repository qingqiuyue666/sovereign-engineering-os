"""
BudgetGovernor: minimum honest AT-027 / INV-021 surface at the governed
inference boundary.

Constitutional anchors:
- v11 §9.8 Budget lifecycle (allocated, active, nearing_limit, exceeded,
  suspended, replenished, closed)
- v11 §22.5 Control Plane authority (budget governance)
- v11 §24.1 AT-027 (exceeded budget suspends or downgrades work without
  granting unsafe shortcuts)
- v11 §24.2 INV-021 (budget thresholds must produce visible governance
  actions; enforcement point = budget transition handler)
- foundation §3 item 10 (phase-1 static budget policy
  `phase1_budget_policy_v1`)
- foundation §3 item 8 / AUDIT-004 (BudgetRecord schema expansion is a
  later-stage hardening target; phase-1 uses in-memory state + AuditRecord
  evidence)

Scope (explicitly narrow):
- in-memory per-task budget state.
- four admissibility cases that the governed inference boundary needs now:
  `active`/`nearing_limit` (admissible), `exceeded` (not admissible),
  `suspended` (not admissible), and "projected consumption would exceed
  hard budget" (not admissible, forces `active -> exceeded -> suspended`).
- every state transition emits a `budget_transition` AuditRecord via the
  injected ledger so replay can reconstruct the governance decision.

Out of scope (explicitly deferred):
- `BudgetRecord` schema / SQL table (AUDIT-004 later-stage hardening).
- `replenished`, `closed` lifecycle paths (no code path in phase-1 needs
  them; we keep the states in the enum but never drive them internally).
- dynamic budget policy / multi-tenant budget classes.
- nearing_limit threshold tuning (AT-026 surface; emitted here because
  the same governor owns the state machine, but no AT-026 test is added
  in this increment).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
from typing import Any, Mapping


class BudgetState(str, Enum):
    """§9.8 budget lifecycle states.

    Phase-1 drives: allocated -> active -> {nearing_limit} ->
    {exceeded -> suspended}. `replenished` and `closed` are declared
    for constitutional completeness but not driven by this increment.
    """

    ALLOCATED = "allocated"
    ACTIVE = "active"
    NEARING_LIMIT = "nearing_limit"
    EXCEEDED = "exceeded"
    SUSPENDED = "suspended"
    REPLENISHED = "replenished"
    CLOSED = "closed"


# Legal transitions from §9.8. Phase-1 only drives the transitions on the
# left of the `|` in each tuple pair; the rest are declared for forward
# compatibility and asserted in `_transition`.
_LEGAL_TRANSITIONS: frozenset[tuple[BudgetState, BudgetState]] = frozenset(
    {
        (BudgetState.ALLOCATED, BudgetState.ACTIVE),
        (BudgetState.ACTIVE, BudgetState.NEARING_LIMIT),
        (BudgetState.NEARING_LIMIT, BudgetState.ACTIVE),
        (BudgetState.NEARING_LIMIT, BudgetState.EXCEEDED),
        (BudgetState.ACTIVE, BudgetState.EXCEEDED),
        (BudgetState.EXCEEDED, BudgetState.SUSPENDED),
        (BudgetState.NEARING_LIMIT, BudgetState.REPLENISHED),
        (BudgetState.SUSPENDED, BudgetState.REPLENISHED),
        (BudgetState.REPLENISHED, BudgetState.ACTIVE),
        (BudgetState.ACTIVE, BudgetState.CLOSED),
        (BudgetState.SUSPENDED, BudgetState.CLOSED),
    }
)


class BudgetExhausted(Exception):
    """Raised when a governed inference attempt is refused by the governor.

    Carries the governance reason so the inference boundary can attach
    it to its failure audit record.
    """

    def __init__(self, *, reason: str, task_id: str, detail: str) -> None:
        super().__init__(f"budget exhausted for task {task_id}: {reason} ({detail})")
        self.reason = reason
        self.task_id = task_id
        self.detail = detail


class BudgetGovernorViolation(Exception):
    """Raised for internal contract breaches (illegal transition, unknown task)."""


@dataclass
class _TaskBudget:
    task_id: str
    hard_budget_tokens: int
    nearing_limit_ratio: float
    consumed: int = 0
    state: BudgetState = BudgetState.ALLOCATED
    budget_policy_id: str = "phase1_budget_policy_v1"
    history: list[Mapping[str, Any]] = field(default_factory=list)


class BudgetGovernor:
    """Per-task token-budget governor for the inference boundary.

    The governor is the single authority that decides whether a task's
    next inference is admissible. Callers MUST:
    - `allocate(task_id, hard_budget_tokens)` once per task.
    - `assert_admissible(task_id, projected_tokens)` before invoking the
      adapter.
    - `record_consumption(task_id, actual_tokens)` after the adapter
      response is parsed AND before the InferenceArtifact is persisted.

    Any transition to `exceeded` drives an immediate transition to
    `suspended` (AT-027: exceeded budget suspends work). Once suspended,
    all further admissibility checks fail-closed with reason
    `budget_already_suspended`.
    """

    def __init__(
        self,
        *,
        audit_ledger: Any,
        default_hard_budget_tokens: int = 96_000,
        nearing_limit_ratio: float = 0.9,
        budget_policy_id: str = "phase1_budget_policy_v1",
    ) -> None:
        if default_hard_budget_tokens <= 0:
            raise BudgetGovernorViolation("default_hard_budget_tokens must be > 0")
        if not (0.0 < nearing_limit_ratio < 1.0):
            raise BudgetGovernorViolation(
                "nearing_limit_ratio must be strictly between 0 and 1"
            )
        self._audit = audit_ledger
        self._default_hard = int(default_hard_budget_tokens)
        self._nearing_ratio = float(nearing_limit_ratio)
        self._policy_id = str(budget_policy_id)
        self._tasks: dict[str, _TaskBudget] = {}
        self._lock = Lock()

    # ------------------------------------------------------------------
    # allocation
    # ------------------------------------------------------------------

    def allocate(
        self,
        *,
        task_id: str,
        hard_budget_tokens: int | None = None,
    ) -> None:
        """Allocate a fresh budget envelope for `task_id`.

        Idempotent: re-allocating a task that is already allocated is a
        no-op (returns without emitting a transition) so test harnesses
        can call this defensively. Re-allocating a task that has entered
        a later state is a contract breach.
        """
        hard = int(hard_budget_tokens if hard_budget_tokens is not None else self._default_hard)
        if hard <= 0:
            raise BudgetGovernorViolation("hard_budget_tokens must be > 0")

        with self._lock:
            existing = self._tasks.get(task_id)
            if existing is not None:
                # `allocate` immediately drives ALLOCATED -> ACTIVE. A
                # re-call with the same hard budget while the task is
                # still in ALLOCATED or ACTIVE (i.e. has not yet
                # consumed budget) is treated as idempotent so the
                # runtime allocation path is safe to call once per
                # `admit_context` even if a caller retries.
                if (
                    existing.state in (BudgetState.ALLOCATED, BudgetState.ACTIVE)
                    and existing.hard_budget_tokens == hard
                    and existing.consumed == 0
                ):
                    return
                raise BudgetGovernorViolation(
                    f"task {task_id} already has a budget in state {existing.state.value}"
                )
            tb = _TaskBudget(
                task_id=task_id,
                hard_budget_tokens=hard,
                nearing_limit_ratio=self._nearing_ratio,
            )
            self._tasks[task_id] = tb

        self._emit_transition(
            tb,
            from_state=None,
            to_state=BudgetState.ALLOCATED,
            reason="budget_allocated",
            detail={
                "hard_budget_tokens": hard,
                "budget_policy_id": self._policy_id,
            },
        )
        # Allocated budgets immediately become active so the first
        # `assert_admissible` does not have to special-case the fresh
        # state. This mirrors §9.8 allocated -> active.
        self._transition(tb, BudgetState.ACTIVE, reason="budget_activated")

    # ------------------------------------------------------------------
    # admissibility
    # ------------------------------------------------------------------

    def assert_admissible(
        self,
        *,
        task_id: str,
        projected_tokens: int,
    ) -> None:
        """Refuse the upcoming inference if governance forbids it.

        AT-027 cases enforced here:
        - budget is already `suspended` -> refuse (`budget_already_suspended`).
        - budget is already `exceeded` -> refuse (`budget_already_exceeded`);
          this state is transient inside `record_consumption` but we
          refuse defensively if a caller observes it.
        - projected consumption would exceed `hard_budget_tokens` ->
          transition `active -> exceeded -> suspended` and refuse
          (`budget_would_be_exceeded`). No unsafe shortcut is granted.
        """
        if projected_tokens < 0:
            raise BudgetGovernorViolation("projected_tokens must be >= 0")

        tb = self._require_task(task_id)

        if tb.state is BudgetState.SUSPENDED:
            raise BudgetExhausted(
                reason="budget_already_suspended",
                task_id=task_id,
                detail=(
                    f"consumed={tb.consumed}, hard_budget={tb.hard_budget_tokens}"
                ),
            )
        if tb.state is BudgetState.EXCEEDED:
            # §9.8 mandates exceeded -> suspended. Drive it and refuse.
            self._transition(
                tb,
                BudgetState.SUSPENDED,
                reason="budget_suspended",
                detail={"trigger": "observed_exceeded_on_admission_check"},
            )
            raise BudgetExhausted(
                reason="budget_already_exceeded",
                task_id=task_id,
                detail=(
                    f"consumed={tb.consumed}, hard_budget={tb.hard_budget_tokens}"
                ),
            )
        if tb.state is BudgetState.CLOSED:
            raise BudgetExhausted(
                reason="budget_closed",
                task_id=task_id,
                detail="closed budgets do not admit further inference",
            )
        if tb.state not in (BudgetState.ACTIVE, BudgetState.NEARING_LIMIT):
            # allocated/replenished should have been driven to active via
            # allocate()/replenish(). Anything else here is a contract bug.
            raise BudgetGovernorViolation(
                f"budget for {task_id} in unexpected state {tb.state.value}"
            )

        if tb.consumed + projected_tokens > tb.hard_budget_tokens:
            detail = {
                "consumed": tb.consumed,
                "projected_tokens": projected_tokens,
                "hard_budget_tokens": tb.hard_budget_tokens,
            }
            self._transition(
                tb,
                BudgetState.EXCEEDED,
                reason="budget_would_be_exceeded",
                detail=detail,
            )
            self._transition(
                tb,
                BudgetState.SUSPENDED,
                reason="budget_suspended",
                detail={"trigger": "budget_would_be_exceeded"},
            )
            raise BudgetExhausted(
                reason="budget_would_be_exceeded",
                task_id=task_id,
                detail=(
                    f"consumed={tb.consumed}, projected={projected_tokens}, "
                    f"hard_budget={tb.hard_budget_tokens}"
                ),
            )

    # ------------------------------------------------------------------
    # consumption
    # ------------------------------------------------------------------

    def record_consumption(
        self,
        *,
        task_id: str,
        actual_tokens: int,
    ) -> None:
        """Record actual consumption after a successful adapter call.

        AT-027 post-flight enforcement:
        - if the new `consumed` exceeds `hard_budget_tokens`, transition
          `active/nearing_limit -> exceeded -> suspended` and raise
          `BudgetExhausted(reason="budget_exceeded_during_inference")`.
          The caller MUST NOT persist the produced InferenceArtifact in
          that case.
        - if the new `consumed` crosses the nearing_limit ratio, emit a
          nearing_limit transition (§9.8 and INV-021 visible-signal
          requirement). This is a signal, not a refusal.
        """
        if actual_tokens < 0:
            raise BudgetGovernorViolation("actual_tokens must be >= 0")

        tb = self._require_task(task_id)
        if tb.state not in (BudgetState.ACTIVE, BudgetState.NEARING_LIMIT):
            raise BudgetGovernorViolation(
                f"cannot record consumption on task {task_id} in state "
                f"{tb.state.value}"
            )

        new_consumed = tb.consumed + int(actual_tokens)
        tb.consumed = new_consumed

        if new_consumed > tb.hard_budget_tokens:
            detail = {
                "consumed": new_consumed,
                "hard_budget_tokens": tb.hard_budget_tokens,
                "overrun_tokens": new_consumed - tb.hard_budget_tokens,
            }
            self._transition(
                tb,
                BudgetState.EXCEEDED,
                reason="budget_exceeded_during_inference",
                detail=detail,
            )
            self._transition(
                tb,
                BudgetState.SUSPENDED,
                reason="budget_suspended",
                detail={"trigger": "budget_exceeded_during_inference"},
            )
            raise BudgetExhausted(
                reason="budget_exceeded_during_inference",
                task_id=task_id,
                detail=(
                    f"consumed={new_consumed}, hard_budget={tb.hard_budget_tokens}"
                ),
            )

        threshold = int(tb.hard_budget_tokens * tb.nearing_limit_ratio)
        if (
            tb.state is BudgetState.ACTIVE
            and new_consumed >= threshold
        ):
            self._transition(
                tb,
                BudgetState.NEARING_LIMIT,
                reason="budget_nearing_limit",
                detail={
                    "consumed": new_consumed,
                    "threshold_tokens": threshold,
                    "hard_budget_tokens": tb.hard_budget_tokens,
                },
            )

    # ------------------------------------------------------------------
    # introspection (for tests and audit callers only)
    # ------------------------------------------------------------------

    def snapshot(self, task_id: str) -> Mapping[str, Any]:
        tb = self._require_task(task_id)
        return {
            "task_id": tb.task_id,
            "state": tb.state.value,
            "consumed": tb.consumed,
            "hard_budget_tokens": tb.hard_budget_tokens,
            "budget_policy_id": tb.budget_policy_id,
            "transitions": list(tb.history),
        }

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _require_task(self, task_id: str) -> _TaskBudget:
        tb = self._tasks.get(task_id)
        if tb is None:
            raise BudgetGovernorViolation(
                f"no budget allocated for task {task_id}"
            )
        return tb

    def _transition(
        self,
        tb: _TaskBudget,
        to_state: BudgetState,
        *,
        reason: str,
        detail: Mapping[str, Any] | None = None,
    ) -> None:
        from_state = tb.state
        if (from_state, to_state) not in _LEGAL_TRANSITIONS:
            raise BudgetGovernorViolation(
                f"illegal budget transition {from_state.value} -> {to_state.value}"
            )
        tb.state = to_state
        self._emit_transition(
            tb,
            from_state=from_state,
            to_state=to_state,
            reason=reason,
            detail=detail,
        )

    def _emit_transition(
        self,
        tb: _TaskBudget,
        *,
        from_state: BudgetState | None,
        to_state: BudgetState,
        reason: str,
        detail: Mapping[str, Any] | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "from_state": from_state.value if from_state is not None else None,
            "to_state": to_state.value,
            "reason": reason,
            "consumed": tb.consumed,
            "hard_budget_tokens": tb.hard_budget_tokens,
            "budget_policy_id": tb.budget_policy_id,
        }
        if detail:
            payload["detail"] = dict(detail)
        tb.history.append(payload)
        self._audit.append(
            record_type="budget_transition",
            task_id=tb.task_id,
            payload=payload,
        )
