"""Real local execution kernel runtime.

v1 — contract-only. No command execution. Exact first-token allowlist.
shlex parsing only. No network. No main mutation. No secrets.
"""

from __future__ import annotations

from .local_execution_kernel import LocalExecutionKernel
from .execution_request import ExecutionRequest
from .command_allowlist import CommandAllowlist
from .execution_preflight import ExecutionPreflight
from .execution_receipt import ExecutionReceipt, ExecutionFailureReceipt, produce_execution_receipt, produce_execution_failure_receipt
from .execution_canonical_hash import ExecutionCanonicalHash
from .execution_security import ExecutionSecurity

__all__ = [
    "LocalExecutionKernel",
    "ExecutionRequest",
    "CommandAllowlist",
    "ExecutionPreflight",
    "ExecutionReceipt",
    "ExecutionFailureReceipt",
    "produce_execution_receipt",
    "produce_execution_failure_receipt",
    "ExecutionCanonicalHash",
    "ExecutionSecurity",
]
