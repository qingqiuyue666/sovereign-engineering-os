"""Deterministic finite state machine with observation metadata separated."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping
import json
import threading

from kernel.audit.hashchain import canonical_json, digest_payload
from kernel.audit.trail import audit
from kernel.errors.hierarchy import InvalidTransitionError

__all__ = ["State", "StateMachine", "Transition", "TransitionReceipt"]

_FORBIDDEN_CONTEXT_KEYS = frozenset({"env_value", "raw_prompt", "raw_provider_response", "secret_value"})


class State(str, Enum):
    """String enum base for domain-specific states."""


@dataclass(frozen=True)
class Transition:
    from_state: str
    to_state: str
    required_context: Mapping[str, object] = field(default_factory=dict)
    description: str = ""


@dataclass(frozen=True)
class TransitionReceipt:
    machine: str
    sequence: int
    from_state: str
    to_state: str
    accepted: bool
    reasons: tuple[str, ...]
    content_hash: str
    observed_at: str

    def deterministic_material(self) -> dict[str, object]:
        return {
            "accepted": self.accepted,
            "from_state": self.from_state,
            "machine": self.machine,
            "reasons": list(self.reasons),
            "sequence": self.sequence,
            "to_state": self.to_state,
        }

    def as_dict(self) -> dict[str, object]:
        payload = self.deterministic_material()
        payload["content_hash"] = self.content_hash
        payload["observed_at"] = self.observed_at
        return payload


class StateMachine:
    """Thread-safe deterministic transition validator."""

    def __init__(
        self,
        initial_state: str,
        transitions: tuple[Transition, ...] | list[Transition],
        *,
        name: str = "state_machine",
    ) -> None:
        if not isinstance(initial_state, str) or not initial_state:
            raise InvalidTransitionError("initial_state_required")
        if not isinstance(name, str) or not name:
            raise InvalidTransitionError("state_machine_name_required")
        self.name = name
        self._state = initial_state
        self._initial_state = initial_state
        self._transitions: dict[str, tuple[Transition, ...]] = {}
        self._history: list[TransitionReceipt] = []
        self._sequence = 0
        self._lock = threading.RLock()
        for transition in transitions:
            self.add_transition(transition)

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    @property
    def history(self) -> tuple[TransitionReceipt, ...]:
        with self._lock:
            return tuple(self._history)

    def add_transition(self, transition: Transition) -> None:
        _validate_transition(transition)
        normalized_transition = Transition(
            from_state=transition.from_state,
            to_state=transition.to_state,
            required_context=_normalize_context(transition.required_context),
            description=transition.description,
        )
        with self._lock:
            current = self._transitions.get(normalized_transition.from_state, ())
            self._transitions[normalized_transition.from_state] = current + (normalized_transition,)

    def available_transitions(self, context: Mapping[str, object] | None = None) -> tuple[str, ...]:
        normalized_context = _normalize_context(context)
        with self._lock:
            available = self._transitions.get(self._state, ())
        return tuple(
            transition.to_state
            for transition in available
            if _context_matches(transition.required_context, normalized_context)
        )

    def can_fire(self, to_state: str, context: Mapping[str, object] | None = None) -> bool:
        return to_state in self.available_transitions(context)

    def fire(
        self,
        to_state: str,
        *,
        context: Mapping[str, object] | None = None,
        observed_at: str | None = None,
    ) -> TransitionReceipt:
        normalized_context = _normalize_context(context)
        observed = _observed_at(observed_at)
        with self._lock:
            from_state = self._state
            transition, reasons = self._match_transition(from_state, to_state, normalized_context)
            sequence = self._sequence + 1
            accepted = transition is not None
            material = {
                "accepted": accepted,
                "from_state": from_state,
                "machine": self.name,
                "reasons": reasons,
                "sequence": sequence,
                "to_state": to_state,
            }
            receipt = TransitionReceipt(
                machine=self.name,
                sequence=sequence,
                from_state=from_state,
                to_state=to_state,
                accepted=accepted,
                reasons=tuple(reasons),
                content_hash=digest_payload(material),
                observed_at=observed,
            )
            if not accepted:
                audit("state_machine.transition_rejected", machine=self.name, from_state=from_state, to_state=to_state, reasons=list(reasons))
                raise InvalidTransitionError(",".join(reasons))
            self._state = to_state
            self._sequence = sequence
            self._history.append(receipt)
        audit("state_machine.transition", machine=self.name, from_state=from_state, to_state=to_state, sequence=sequence)
        return receipt

    def deterministic_history(self) -> tuple[dict[str, object], ...]:
        with self._lock:
            return tuple(receipt.deterministic_material() for receipt in self._history)

    def reset(self, *, observed_at: str | None = None) -> None:
        _observed_at(observed_at)
        with self._lock:
            self._state = self._initial_state
            self._history.clear()
            self._sequence = 0
        audit("state_machine.reset", machine=self.name)

    def _match_transition(
        self,
        from_state: str,
        to_state: str,
        context: Mapping[str, object],
    ) -> tuple[Transition | None, list[str]]:
        matched_target = False
        for transition in self._transitions.get(from_state, ()):
            if transition.to_state != to_state:
                continue
            matched_target = True
            if _context_matches(transition.required_context, context):
                return transition, []
        if matched_target:
            return None, [f"guard_failed:{from_state}->{to_state}"]
        return None, [f"invalid_transition:{from_state}->{to_state}"]


def _validate_transition(transition: Transition) -> None:
    if not isinstance(transition.from_state, str) or not transition.from_state:
        raise InvalidTransitionError("transition_from_state_required")
    if not isinstance(transition.to_state, str) or not transition.to_state:
        raise InvalidTransitionError("transition_to_state_required")
    _normalize_context(transition.required_context)


def _normalize_context(context: Mapping[str, object] | None) -> dict[str, Any]:
    if context is None:
        return {}
    if not isinstance(context, Mapping):
        raise InvalidTransitionError("state_context_must_be_mapping")
    _reject_forbidden_context(context)
    try:
        return json.loads(canonical_json(dict(context)))
    except (TypeError, ValueError) as exc:
        raise InvalidTransitionError("state_context_must_be_canonical_json") from exc


def _reject_forbidden_context(value: object) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key) in _FORBIDDEN_CONTEXT_KEYS:
                raise InvalidTransitionError(f"state_context_forbidden_key:{key}")
            _reject_forbidden_context(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_forbidden_context(item)


def _context_matches(required: Mapping[str, object], context: Mapping[str, object]) -> bool:
    for key, value in required.items():
        if context.get(key) != value:
            return False
    return True


def _observed_at(value: str | None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if not isinstance(value, str) or not value:
        raise InvalidTransitionError("observed_at_must_be_nonempty_string")
    return value
