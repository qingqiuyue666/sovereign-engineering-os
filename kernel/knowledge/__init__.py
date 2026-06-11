"""SEOS Knowledge Layer.

This package exposes human-facing knowledge and vault adapters while keeping
SEOS task contracts, approvals, permits, execution receipts, and evidence traces
as the authority layer.
"""

from kernel.knowledge.graph import build_workspace_graph, write_workspace_graph
from kernel.knowledge.object_model import KnowledgeObject, KnowledgeRelation
from kernel.knowledge.vault import export_task_to_vault, export_workspace_to_vault, init_control_vault
from kernel.knowledge.vault_scanner import scan_control_vault

__all__ = [
    "KnowledgeObject",
    "KnowledgeRelation",
    "build_workspace_graph",
    "export_task_to_vault",
    "export_workspace_to_vault",
    "init_control_vault",
    "scan_control_vault",
    "write_workspace_graph",
]
