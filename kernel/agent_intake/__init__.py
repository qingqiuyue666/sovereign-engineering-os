"""SEOS agent-intake boundary.

Agent intake converts external AI/agent/MCP requests into bounded proposals or
read-only manifests. It does not create approvals, permits, or executions.
"""

from kernel.agent_intake.boundary import evaluate_agent_request
from kernel.agent_intake.proposals import write_agent_proposal

__all__ = ["evaluate_agent_request", "write_agent_proposal"]
