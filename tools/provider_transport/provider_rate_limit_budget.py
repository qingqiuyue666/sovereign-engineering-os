"""Provider rate-limit and budget contract — hard enforcement.

Budget and rate limits are pre-configured per provider. Every execution
consumes budget and rate-limit tokens. Exceeding either limit rejects
the transport. Budget limit is a float; rate limit is an integer.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class RateLimitBudgetResult:
    """Immutable result of budget and rate-limit validation."""
    valid: bool
    provider_id: str
    budget_limit: float
    budget_consumed: float
    budget_remaining: float
    rate_limit: int
    rate_limit_consumed: int
    rate_limit_remaining: int
    failures: tuple[str, ...]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "provider_id": self.provider_id,
            "budget_limit": self.budget_limit,
            "budget_consumed": self.budget_consumed,
            "budget_remaining": self.budget_remaining,
            "rate_limit": self.rate_limit,
            "rate_limit_consumed": self.rate_limit_consumed,
            "rate_limit_remaining": self.rate_limit_remaining,
            "failures": list(self.failures),
        }


# Default limits for known providers (non-zero for mock testing)
DEFAULT_BUDGET_LIMITS: Dict[str, float] = {
    "mock-finance": 1000.0,
    "mock-market-data": 500.0,
    "mock-news": 200.0,
    "mock-weather": 100.0,
}

DEFAULT_RATE_LIMITS: Dict[str, int] = {
    "mock-finance": 100,
    "mock-market-data": 200,
    "mock-news": 300,
    "mock-weather": 500,
}


def validate_rate_limit_budget(
    provider_id: str,
    budget_consumed: float = 0.0,
    budget_limit: float = 0.0,
    rate_limit_consumed: int = 0,
    rate_limit: int = 0,
) -> RateLimitBudgetResult:
    """Validate budget and rate-limit constraints for a provider.

    Args:
        provider_id: The provider to check.
        budget_consumed: Total budget consumed so far.
        budget_limit: Maximum allowed budget.
        rate_limit_consumed: Total rate-limit tokens consumed.
        rate_limit: Maximum allowed rate-limit tokens.

    Returns:
        RateLimitBudgetResult with validation details.
    """
    failures: list[str] = []

    if not isinstance(provider_id, str) or not provider_id.strip():
        failures.append("provider_id_must_be_nonempty_string")

    # Use defaults if limits not specified
    effective_budget_limit = budget_limit if budget_limit > 0 else DEFAULT_BUDGET_LIMITS.get(provider_id, 0.0)
    effective_rate_limit = rate_limit if rate_limit > 0 else DEFAULT_RATE_LIMITS.get(provider_id, 0)

    # Type validation
    if not isinstance(budget_consumed, (int, float)) or budget_consumed < 0:
        failures.append("budget_consumed_must_be_nonnegative_number")
    if not isinstance(budget_limit, (int, float)) or budget_limit < 0:
        failures.append("budget_limit_must_be_nonnegative_number")
    if not isinstance(rate_limit_consumed, int) or rate_limit_consumed < 0:
        failures.append("rate_limit_consumed_must_be_nonnegative_int")
    if not isinstance(rate_limit, int) or rate_limit < 0:
        failures.append("rate_limit_must_be_nonnegative_int")

    budget_remaining = effective_budget_limit - budget_consumed
    rate_limit_remaining = effective_rate_limit - rate_limit_consumed

    if budget_remaining < 0:
        failures.append(
            f"budget_exceeded: consumed={budget_consumed:.2f} limit={effective_budget_limit:.2f}"
        )
    if rate_limit_remaining <= 0 and effective_rate_limit > 0:
        failures.append(
            f"rate_limit_exhausted: consumed={rate_limit_consumed} limit={effective_rate_limit}"
        )

    return RateLimitBudgetResult(
        valid=len(failures) == 0,
        provider_id=provider_id,
        budget_limit=effective_budget_limit,
        budget_consumed=budget_consumed,
        budget_remaining=max(0.0, budget_remaining),
        rate_limit=effective_rate_limit,
        rate_limit_consumed=rate_limit_consumed,
        rate_limit_remaining=max(0, rate_limit_remaining),
        failures=tuple(failures),
    )
