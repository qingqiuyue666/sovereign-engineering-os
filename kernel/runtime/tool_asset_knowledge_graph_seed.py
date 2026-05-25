"""Tool / asset knowledge graph seed v1.

Defines a minimal in-repo graph schema linking tools, assets, workflows,
capabilities, risks, and candidate substrates. Candidate projects are metadata
only: they are not imported, installed, vendored, or runtime-integrated.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

__all__ = [
    "REQUIRED_EDGE_TYPES",
    "REQUIRED_NODE_TYPES",
    "REQUIRED_CANDIDATE_LINKS",
    "AssetNode",
    "CandidateSubstrateNode",
    "CapabilityNode",
    "DCCAppNode",
    "DependencyNode",
    "GraphEdge",
    "KnowledgeGraphSeed",
    "MCPServerNode",
    "ModelNode",
    "ProjectNode",
    "RiskNode",
    "ToolNode",
    "WorkflowNode",
    "build_knowledge_graph_seed",
    "validate_knowledge_graph_seed",
]

REQUIRED_NODE_TYPES = (
    "ToolNode",
    "AssetNode",
    "WorkflowNode",
    "CapabilityNode",
    "RiskNode",
    "CandidateSubstrateNode",
    "DependencyNode",
    "ModelNode",
    "MCPServerNode",
    "DCCAppNode",
    "ProjectNode",
)

REQUIRED_EDGE_TYPES = (
    "CAN_EXECUTE",
    "PRODUCES",
    "CONSUMES",
    "DEPENDS_ON",
    "COMPATIBLE_WITH",
    "RISK_OF",
    "REPLACES",
    "CANDIDATE_FOR",
    "OBSERVED_IN",
    "APPROVED_FOR",
)

REQUIRED_CANDIDATE_LINKS = {
    "temporal": "https://github.com/temporalio/temporal",
    "temporal_python_sdk": "https://github.com/temporalio/sdk-python",
    "nats_server": "https://github.com/nats-io/nats-server",
    "nats_python": "https://github.com/nats-io/nats.py",
    "lancedb": "https://github.com/lancedb/lancedb",
    "duckdb": "https://github.com/duckdb/duckdb",
    "sqlite": "https://github.com/sqlite/sqlite",
    "extism": "https://github.com/extism/extism",
    "wasmtime": "https://github.com/bytecodealliance/wasmtime",
    "openusd": "https://github.com/PixarAnimationStudios/OpenUSD",
    "materialx": "https://github.com/AcademySoftwareFoundation/MaterialX",
    "opentimelineio": "https://github.com/AcademySoftwareFoundation/OpenTimelineIO",
    "opencolorio": "https://github.com/AcademySoftwareFoundation/OpenColorIO",
    "openimageio": "https://github.com/AcademySoftwareFoundation/OpenImageIO",
    "openexr": "https://github.com/AcademySoftwareFoundation/openexr",
    "tauri": "https://github.com/tauri-apps/tauri",
    "opentelemetry": "https://github.com/open-telemetry/opentelemetry-collector",
    "phoenix": "https://github.com/Arize-ai/phoenix",
    "langfuse": "https://github.com/langfuse/langfuse",
    "ragas": "https://github.com/explodinggradients/ragas",
    "deepeval": "https://github.com/confident-ai/deepeval",
    "promptfoo": "https://github.com/promptfoo/promptfoo",
    "opa": "https://github.com/open-policy-agent/opa",
    "cedar": "https://github.com/cedar-policy/cedar",
    "semgrep": "https://github.com/semgrep/semgrep",
    "codeql": "https://github.com/github/codeql",
    "trivy": "https://github.com/aquasecurity/trivy",
    "syft": "https://github.com/anchore/syft",
    "grype": "https://github.com/anchore/grype",
    "osv_scanner": "https://github.com/google/osv-scanner",
    "restic": "https://github.com/restic/restic",
    "dvc": "https://github.com/iterative/dvc",
    "lakefs": "https://github.com/treeverse/lakeFS",
    "openlineage": "https://github.com/OpenLineage/OpenLineage",
    "nix": "https://github.com/NixOS/nix",
    "devbox": "https://github.com/jetify-com/devbox",
    "mise": "https://github.com/jdx/mise",
    "uv": "https://github.com/astral-sh/uv",
    "comfyui": "https://github.com/comfyanonymous/ComfyUI",
    "comfyui_manager": "https://github.com/ltdrdata/ComfyUI-Manager",
    "mcp_servers": "https://github.com/modelcontextprotocol/servers",
    "mcp_python_sdk": "https://github.com/modelcontextprotocol/python-sdk",
    "mcp_typescript_sdk": "https://github.com/modelcontextprotocol/typescript-sdk",
    "github_mcp_server": "https://github.com/github/github-mcp-server",
    "playwright_mcp": "https://github.com/microsoft/playwright-mcp",
    "aider": "https://github.com/Aider-AI/aider",
    "openhands": "https://github.com/All-Hands-AI/OpenHands",
    "swe_agent": "https://github.com/SWE-agent/SWE-agent",
    "langgraph": "https://github.com/langchain-ai/langgraph",
    "autogen": "https://github.com/microsoft/autogen",
    "crewai": "https://github.com/crewAIInc/crewAI",
    "openai_agents_sdk": "https://github.com/openai/openai-agents-python",
    "pydanticai": "https://github.com/pydantic/pydantic-ai",
    "dspy": "https://github.com/stanfordnlp/dspy",
}


@dataclass(frozen=True)
class ToolNode:
    node_id: str
    name: str
    capability_id: str
    executable: bool
    production_approved: bool = False

    node_type: str = "ToolNode"


@dataclass(frozen=True)
class AssetNode:
    node_id: str
    name: str
    media_class: str
    production_approved: bool = False

    node_type: str = "AssetNode"


@dataclass(frozen=True)
class WorkflowNode:
    node_id: str
    name: str
    domain: str
    production_approved: bool = False

    node_type: str = "WorkflowNode"


@dataclass(frozen=True)
class CapabilityNode:
    node_id: str
    name: str
    description: str
    production_approved: bool = False

    node_type: str = "CapabilityNode"


@dataclass(frozen=True)
class RiskNode:
    node_id: str
    name: str
    risk_class: str

    node_type: str = "RiskNode"


@dataclass(frozen=True)
class CandidateSubstrateNode:
    candidate_id: str
    github_url: str
    domain: str
    role: str
    solves: str
    does_not_solve: str
    integration_phase: str
    direct_dependency_allowed_now: bool
    runtime_integration_allowed_now: bool
    risk_class: str
    production_approved: bool = False

    node_type: str = "CandidateSubstrateNode"


@dataclass(frozen=True)
class DependencyNode:
    node_id: str
    name: str
    dependency_kind: str
    production_approved: bool = False

    node_type: str = "DependencyNode"


@dataclass(frozen=True)
class ModelNode:
    node_id: str
    name: str
    provider: str
    production_approved: bool = False

    node_type: str = "ModelNode"


@dataclass(frozen=True)
class MCPServerNode:
    node_id: str
    name: str
    transport: str
    production_approved: bool = False

    node_type: str = "MCPServerNode"


@dataclass(frozen=True)
class DCCAppNode:
    node_id: str
    name: str
    launch_allowed_now: bool
    production_approved: bool = False

    node_type: str = "DCCAppNode"


@dataclass(frozen=True)
class ProjectNode:
    node_id: str
    name: str
    repository: str
    production_approved: bool = False

    node_type: str = "ProjectNode"


@dataclass(frozen=True)
class GraphEdge:
    edge_type: str
    source_id: str
    target_id: str
    evidence: str


@dataclass(frozen=True)
class KnowledgeGraphSeed:
    nodes: tuple[object, ...]
    edges: tuple[GraphEdge, ...]

    def as_dict(self) -> dict[str, object]:
        return {
            "nodes": [asdict(node) for node in self.nodes],
            "edges": [asdict(edge) for edge in self.edges],
        }


def build_knowledge_graph_seed() -> KnowledgeGraphSeed:
    project = ProjectNode(
        node_id="project_sovereign_engineering_os",
        name="Sovereign Engineering OS",
        repository="qqyqqyqqy666-wq/sovereign-engineering-os",
        production_approved=True,
    )
    nodes: list[object] = [
        project,
        CapabilityNode(
            node_id="capability_command_admission",
            name="Command admission",
            description="Command-id-only admission before local validation.",
            production_approved=True,
        ),
        CapabilityNode(
            node_id="capability_asset_awareness",
            name="Asset awareness",
            description="Read-only deterministic local asset inventory.",
        ),
        RiskNode(
            node_id="risk_raw_command_execution",
            name="Raw command execution",
            risk_class="HIGH_RISK",
        ),
        ToolNode(
            node_id="tool_command_envelope_router",
            name="Command envelope admission router",
            capability_id="capability_command_admission",
            executable=True,
            production_approved=True,
        ),
        AssetNode(
            node_id="asset_minimal_inventory_record",
            name="Minimal asset inventory record",
            media_class="METADATA",
        ),
        WorkflowNode(
            node_id="workflow_asset_ingestion",
            name="Asset ingestion descriptor workflow",
            domain="ASSET_INGESTION",
        ),
        DependencyNode(
            node_id="dependency_python_stdlib",
            name="Python standard library",
            dependency_kind="allowed_runtime_foundation",
            production_approved=True,
        ),
        ModelNode(
            node_id="model_no_runtime_model",
            name="No model runtime in seed",
            provider="none",
        ),
        MCPServerNode(
            node_id="mcp_metadata_only",
            name="MCP servers candidate metadata only",
            transport="none",
        ),
        DCCAppNode(
            node_id="dcc_apps_candidate_only",
            name="DCC applications candidate only",
            launch_allowed_now=False,
        ),
    ]
    nodes.extend(_candidate_nodes())
    edges = _base_edges()
    edges.extend(_candidate_edges())
    return KnowledgeGraphSeed(nodes=tuple(nodes), edges=tuple(edges))


def validate_knowledge_graph_seed(seed: KnowledgeGraphSeed) -> tuple[str, ...]:
    failures: list[str] = []
    node_types = {getattr(node, "node_type", type(node).__name__) for node in seed.nodes}
    for node_type in REQUIRED_NODE_TYPES:
        if node_type not in node_types:
            failures.append(f"missing_node_type:{node_type}")
    edge_types = {edge.edge_type for edge in seed.edges}
    for edge_type in REQUIRED_EDGE_TYPES:
        if edge_type not in edge_types:
            failures.append(f"missing_edge_type:{edge_type}")
    candidate_urls = {
        node.github_url
        for node in seed.nodes
        if isinstance(node, CandidateSubstrateNode)
    }
    for github_url in REQUIRED_CANDIDATE_LINKS.values():
        if github_url not in candidate_urls:
            failures.append(f"missing_candidate_url:{github_url}")
    for node in seed.nodes:
        if isinstance(node, CandidateSubstrateNode):
            if node.direct_dependency_allowed_now:
                failures.append(f"candidate_direct_dependency_allowed:{node.candidate_id}")
            if node.runtime_integration_allowed_now:
                failures.append(f"candidate_runtime_integration_allowed:{node.candidate_id}")
        if isinstance(node, ToolNode) and node.executable:
            if not _has_edge(seed, "RISK_OF", node.node_id):
                failures.append(f"executable_tool_missing_risk_edge:{node.node_id}")
        if getattr(node, "production_approved", False):
            node_id = getattr(node, "node_id", getattr(node, "candidate_id", ""))
            if not _has_edge(seed, "APPROVED_FOR", node_id):
                failures.append(f"production_approval_missing_edge:{node_id}")
    return tuple(failures)


def _candidate_nodes() -> tuple[CandidateSubstrateNode, ...]:
    return tuple(
        CandidateSubstrateNode(
            candidate_id=candidate_id,
            github_url=github_url,
            domain=_candidate_domain(candidate_id),
            role=_candidate_role(candidate_id),
            solves=_candidate_solves(candidate_id),
            does_not_solve="Does not authorize immediate dependency adoption, runtime integration, credentials, network calls, tool launch, or production autonomy.",
            integration_phase="candidate_metadata_only",
            direct_dependency_allowed_now=False,
            runtime_integration_allowed_now=False,
            risk_class=_candidate_risk(candidate_id),
        )
        for candidate_id, github_url in REQUIRED_CANDIDATE_LINKS.items()
    )


def _base_edges() -> list[GraphEdge]:
    return [
        GraphEdge(
            "APPROVED_FOR",
            "project_sovereign_engineering_os",
            "project_sovereign_engineering_os",
            "Project node approved as graph root.",
        ),
        GraphEdge(
            "APPROVED_FOR",
            "capability_command_admission",
            "project_sovereign_engineering_os",
            "Command admission is an approved local capability.",
        ),
        GraphEdge(
            "APPROVED_FOR",
            "tool_command_envelope_router",
            "capability_command_admission",
            "Tool is approved for command-id-only admission.",
        ),
        GraphEdge(
            "APPROVED_FOR",
            "dependency_python_stdlib",
            "project_sovereign_engineering_os",
            "Standard library is approved dependency foundation.",
        ),
        GraphEdge(
            "CAN_EXECUTE",
            "tool_command_envelope_router",
            "workflow_asset_ingestion",
            "Only registry-defined validation command ids may be admitted.",
        ),
        GraphEdge(
            "PRODUCES",
            "workflow_asset_ingestion",
            "asset_minimal_inventory_record",
            "Asset ingestion produces inventory metadata.",
        ),
        GraphEdge(
            "CONSUMES",
            "workflow_asset_ingestion",
            "asset_minimal_inventory_record",
            "Workflow consumes prior inventory records for comparison.",
        ),
        GraphEdge(
            "DEPENDS_ON",
            "tool_command_envelope_router",
            "dependency_python_stdlib",
            "Router depends only on Python standard library.",
        ),
        GraphEdge(
            "RISK_OF",
            "tool_command_envelope_router",
            "risk_raw_command_execution",
            "Executable-capable tool must carry explicit risk edge.",
        ),
        GraphEdge(
            "OBSERVED_IN",
            "asset_minimal_inventory_record",
            "project_sovereign_engineering_os",
            "Inventory record observed in this project spine.",
        ),
    ]


def _candidate_edges() -> list[GraphEdge]:
    edges: list[GraphEdge] = []
    for candidate_id in REQUIRED_CANDIDATE_LINKS:
        edges.append(
            GraphEdge(
                "CANDIDATE_FOR",
                candidate_id,
                _candidate_capability_target(candidate_id),
                "Candidate substrate recorded for future evaluation only.",
            )
        )
        edges.append(
            GraphEdge(
                "COMPATIBLE_WITH",
                candidate_id,
                "project_sovereign_engineering_os",
                "Compatibility is metadata-only and not runtime admission.",
            )
        )
    edges.append(
        GraphEdge(
            "REPLACES",
            "sqlite",
            "dependency_python_stdlib",
            "SQLite may replace ad hoc file journals only after approval.",
        )
    )
    return edges


def _candidate_domain(candidate_id: str) -> str:
    if candidate_id in {"temporal", "temporal_python_sdk", "nats_server", "nats_python"}:
        return "orchestration"
    if candidate_id in {"lancedb", "duckdb", "sqlite", "dvc", "lakefs", "openlineage"}:
        return "data_and_lineage"
    if candidate_id in {"extism", "wasmtime"}:
        return "plugin_sandbox"
    if candidate_id in {"openusd", "materialx", "opentimelineio", "opencolorio", "openimageio", "openexr"}:
        return "creative_pipeline"
    if candidate_id in {"tauri"}:
        return "operator_shell"
    if candidate_id in {"opentelemetry", "phoenix", "langfuse", "ragas", "deepeval", "promptfoo"}:
        return "observability_and_eval"
    if candidate_id in {"opa", "cedar", "semgrep", "codeql", "trivy", "syft", "grype", "osv_scanner"}:
        return "policy_and_security"
    if candidate_id in {"restic", "nix", "devbox", "mise", "uv"}:
        return "local_reproducibility"
    if candidate_id in {"comfyui", "comfyui_manager"}:
        return "ai_image_workflow"
    if "mcp" in candidate_id:
        return "mcp"
    return "agent_framework"


def _candidate_role(candidate_id: str) -> str:
    return candidate_id.replace("_", " ") + " candidate substrate"


def _candidate_solves(candidate_id: str) -> str:
    return "Potential future substrate for " + _candidate_domain(candidate_id) + " after explicit evaluation."


def _candidate_risk(candidate_id: str) -> str:
    high = {"comfyui", "comfyui_manager", "playwright_mcp", "openhands", "aider", "swe_agent"}
    medium = {"temporal", "nats_server", "lancedb", "openusd", "tauri"}
    if candidate_id in high:
        return "HIGH_RISK"
    if candidate_id in medium:
        return "MEDIUM_RISK"
    return "LOW_RISK"


def _candidate_capability_target(candidate_id: str) -> str:
    if candidate_id in {"comfyui", "comfyui_manager", "openusd", "materialx"}:
        return "capability_asset_awareness"
    return "capability_command_admission"


def _has_edge(seed: KnowledgeGraphSeed, edge_type: str, source_id: str) -> bool:
    return any(
        edge.edge_type == edge_type and edge.source_id == source_id
        for edge in seed.edges
    )
