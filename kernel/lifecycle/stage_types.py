"""
Stage types and legal transition guards for the current-stage signable path.

Constitutional anchors:
- v11 §24.3, §31 (current-stage signable path)
- v11 §9.5 / §9.6 (lifecycle transition legality semantics reused)
- v11 §22.10 (invariant binding: INV-018 legal lifecycle transitions)
- implementation foundation §2, §6, §8

Scope lock (phase 1):
  Context -> Inference -> PatchProposal -> Validation -> Review -> Approval
  -> Revision Seal -> Evidence

This module provides:
- `Stage` enum: the eight ordered stages of the signable path
- `LEGAL_TRANSITIONS`: the only legal forward transitions (plus an explicit
  `abandoned` terminal that any non-terminal stage may enter)
- `is_legal_transition` / `assert_legal_transition`: guard primitives used
  by the orchestrator to refuse out-of-path operations fail-closed

Any transition not enumerated here is forbidden and must be rejected.
No "almost legal" transitions are admitted. No state may be skipped.
"""

from __future__ import annotations

from enum import Enum
from typing import FrozenSet, Mapping


class Stage(str, Enum):
    """Canonical ordered stages of the phase-1 signable path.

    Order is load-bearing: it encodes the §24.3 / §31 narrow-path contract.
    """

    CONTEXT = "context"
    INFERENCE = "inference"
    PATCH_PROPOSAL = "patch_proposal"
    VALIDATION = "validation"
    REVIEW = "review"
    APPROVAL = "approval"
    REVISION_SEAL = "revision_seal"
    EVIDENCE = "evidence"

    # Explicit non-forward terminals.
    # `abandoned` captures §9.1 pending -> abandoned at any non-sealed stage.
    # `sealed` is a success terminal produced strictly after Evidence closure.
    ABANDONED = "abandoned"
    SEALED = "sealed"


# Ordered forward path. This list is the single source of truth for
# successor lookup. It is intentionally explicit (not derived from enum
# ordering) because Python enum ordering is not a governance contract.
ORDERED_PATH: tuple[Stage, ...] = (
    Stage.CONTEXT,
    Stage.INFERENCE,
    Stage.PATCH_PROPOSAL,
    Stage.VALIDATION,
    Stage.REVIEW,
    Stage.APPROVAL,
    Stage.REVISION_SEAL,
    Stage.EVIDENCE,
)


def _build_legal_transitions() -> Mapping[Stage, FrozenSet[Stage]]:
    """Construct the legal-transition table.

    Legal forward moves: N -> N+1 only.
    Legal terminal moves from any non-terminal stage: -> ABANDONED.
    Evidence -> SEALED is the only success terminal (Evidence closure rule).
    ABANDONED and SEALED have no outgoing transitions.
    """
    table: dict[Stage, set[Stage]] = {}
    for idx, stage in enumerate(ORDERED_PATH):
        successors: set[Stage] = set()
        if idx + 1 < len(ORDERED_PATH):
            successors.add(ORDERED_PATH[idx + 1])
        successors.add(Stage.ABANDONED)
        if stage is Stage.EVIDENCE:
            successors.add(Stage.SEALED)
        table[stage] = successors
    table[Stage.ABANDONED] = set()
    table[Stage.SEALED] = set()
    return {k: frozenset(v) for k, v in table.items()}


LEGAL_TRANSITIONS: Mapping[Stage, FrozenSet[Stage]] = _build_legal_transitions()


class IllegalStageTransition(Exception):
    """Raised when an out-of-path stage transition is attempted.

    The orchestrator must treat this as a fail-closed governance event and
    emit an AuditRecord (and, where a DriftEventRecord is warranted, a
    DriftEventRecord) rather than silently routing around it.
    """


def is_legal_transition(current: Stage, target: Stage) -> bool:
    """Return True iff `current -> target` is an enumerated legal transition."""
    return target in LEGAL_TRANSITIONS.get(current, frozenset())


def assert_legal_transition(current: Stage, target: Stage) -> None:
    """Fail-closed assertion wrapper for use at stage-admission points."""
    if not is_legal_transition(current, target):
        raise IllegalStageTransition(
            f"illegal stage transition: {current.value} -> {target.value}"
        )


def successor_of(stage: Stage) -> Stage | None:
    """Return the forward successor of `stage` on the ordered path, or None."""
    try:
        idx = ORDERED_PATH.index(stage)
    except ValueError:
        return None
    if idx + 1 >= len(ORDERED_PATH):
        return None
    return ORDERED_PATH[idx + 1]
