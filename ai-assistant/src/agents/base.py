"""
Base PydanticAI Agent Configuration for Qubinode.

Provides common configuration, validators, and utilities
for all agents in the multi-agent architecture.

Per ADR-0063: PydanticAI Core Agent Orchestrator
Per ADR-0049: Multi-Agent LLM Memory Architecture
"""

import os
import logging
from typing import TypeVar, Optional, Any, List

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext, ModelRetry

# Optional Logfire integration
try:
    import logfire

    LOGFIRE_AVAILABLE = True
except ImportError:
    LOGFIRE_AVAILABLE = False
    logfire = None

# Optional MCP integration
try:
    from pydantic_ai.mcp import MCPServerHTTP

    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    MCPServerHTTP = None

# For async context manager support
from contextlib import asynccontextmanager

# Import domain models - try relative first, then absolute
try:
    from ..models.domain import (
        DeploymentResult,
        TaskResult,
        ConfidenceLevel,  # noqa: F401
        RAGSource,  # noqa: F401
    )
except ImportError:
    from models.domain import (
        DeploymentResult,
        TaskResult,
    )

logger = logging.getLogger(__name__)

# Type variable for generic agent results
T = TypeVar("T", bound=BaseModel)


def configure_logfire() -> bool:
    """Configure Logfire for observability if available."""
    if not LOGFIRE_AVAILABLE:
        logger.info("Logfire not available - observability disabled")
        return False

    token = os.getenv("LOGFIRE_TOKEN")
    if not token:
        logger.info("LOGFIRE_TOKEN not set - observability disabled")
        return False

    logfire.configure(
        service_name="qubinode-pydanticai",
        environment=os.getenv("ENVIRONMENT", "development"),
    )
    logfire.instrument_pydantic_ai()
    logger.info("Logfire configured for PydanticAI observability")
    return True


# Configure Logfire on module load
configure_logfire()


class AgentDependencies(BaseModel):
    """
    Dependencies injected into agent runs.

    These are passed to every agent invocation and provide
    session context, configuration, thresholds, and shared services.

    Per ADR-0049: All agents have access to RAG and lineage context.
    """

    session_id: str
    user_role: str = "operator"
    environment: str = "development"
    confidence_threshold: float = 0.6  # Per ADR-0049 Policy 1
    max_retries: int = 3

    # Shared services (injected from AgentContextManager)
    rag_service: Any = Field(default=None, description="RAG service for document retrieval")
    lineage_service: Any = Field(default=None, description="Marquez lineage service")

    # Cached context from RAG/lineage queries
    rag_context: List[str] = Field(default_factory=list, description="Retrieved RAG contexts")
    rag_sources: List[str] = Field(default_factory=list, description="RAG source files")
    lineage_context: dict = Field(default_factory=dict, description="Lineage execution history")

    class Config:
        arbitrary_types_allowed = True


def create_mcp_connection(url: Optional[str] = None) -> Optional["MCPServerHTTP"]:
    """
    Create connection to Qubinode CE-MCP server (ADR-0064).

    The CE-MCP server at localhost:8889 provides 4 meta-tools:
    - discover_tools: Find available tools by category
    - run_code: Execute Python code in sandboxed environment
    - summarize_data: Reduce large outputs for context efficiency
    - quick_action: Common operations without writing code

    These meta-tools provide access to 20 domain tools:
    - dag: list_dags, get_dag_info, trigger_dag
    - vm: list_vms, get_vm_info, create_vm, delete_vm, preflight_vm_creation
    - rag: query_rag, ingest_to_rag, search_similar_errors, manage_rag_documents
    - troubleshoot: diagnose_issue, get_troubleshooting_history, log_troubleshooting_attempt, get_workflow_guidance
    - lineage: get_dag_lineage, get_failure_blast_radius
    - status: get_airflow_status, get_system_info

    Note: MCP servers must be used as async context managers with agents.
    See create_deployment_agent_with_mcp() for proper usage.
    """
    if not MCP_AVAILABLE:
        logger.warning("MCP not available - agent will run without MCP tools")
        return None

    mcp_url = url or os.getenv("QUBINODE_MCP_URL", "http://localhost:8889/sse")
    return MCPServerHTTP(url=mcp_url)


def confidence_validator(min_confidence: float = 0.6):
    """
    Factory for confidence validation decorators.

    Per ADR-0049 Policy 1:
    - High (>=0.8): Proceed with task autonomously
    - Medium (0.6-0.8): Proceed with caveats
    - Low (<0.6): STOP and escalate

    Usage:
        @agent.output_validator
        async def validate(ctx, output):
            return await confidence_validator(0.6)(ctx, output)
    """

    async def validator(ctx: RunContext, output: T) -> T:
        if hasattr(output, "confidence"):
            if output.confidence < min_confidence:
                raise ModelRetry(f"Low confidence ({output.confidence:.2f} < {min_confidence}). Need more RAG context. Query for additional documents.")

            # Add caveats for medium confidence
            if output.confidence < 0.8 and hasattr(output, "next_steps"):
                if not output.next_steps:
                    output.next_steps = [
                        "Review output with human operator",
                        "Verify against documentation",
                    ]

        return output

    return validator


# ============================================================================
# Agent Templates
# ============================================================================


def create_deployment_agent(
    model: Optional[str] = None,
) -> Agent[AgentDependencies, DeploymentResult]:
    """
    Create a deployment agent WITHOUT MCP integration.

    This agent handles infrastructure deployment operations:
    - VM provisioning via kcli
    - Cluster deployments
    - Service configurations

    For MCP integration, use create_deployment_agent_with_mcp() instead.

    Args:
        model: Model identifier in PydanticAI format (provider:model)
               Examples: google-gla:gemini-2.0-flash, openai:gpt-4o

    Returns:
        Configured PydanticAI Agent with DeploymentResult output type
    """
    # PydanticAI model format: provider:model
    model = model or os.getenv("PYDANTICAI_MODEL", "google-gla:gemini-2.0-flash")

    agent = Agent(
        model,
        output_type=DeploymentResult,
        deps_type=AgentDependencies,
        system_prompt="""You are a Qubinode infrastructure deployment assistant.

Your role is to help with infrastructure deployment operations:
- VM provisioning via kcli
- Cluster deployments
- Service configurations

CONFIDENCE SCORING (per ADR-0049 Policy 1):
Always compute confidence scores based on:
- Clarity of the request (40% weight)
- Availability of required information (30% weight)
- Complexity of the operation (20% weight)
- Similar past deployments knowledge (10% weight)

If confidence is below 0.6, request additional information before proceeding.
Set escalation_needed=True if you cannot achieve 0.6 confidence.
""",
    )

    @agent.output_validator
    async def validate_confidence(ctx: RunContext[AgentDependencies], output: DeploymentResult) -> DeploymentResult:
        """Validate confidence meets threshold, retry if not."""
        threshold = ctx.deps.confidence_threshold

        if output.confidence < threshold:
            raise ModelRetry(f"Confidence {output.confidence:.2f} below threshold {threshold}. Request more context or information.")

        return output

    return agent


@asynccontextmanager
async def create_deployment_agent_with_mcp(
    model: Optional[str] = None,
    mcp_url: Optional[str] = None,
):
    """
    Create a deployment agent WITH MCP integration as async context manager.

    MCP servers must be used within an async context manager. Example usage:

        async with create_deployment_agent_with_mcp() as agent:
            result = await agent.run("Deploy a VM", deps=deps)

    Args:
        model: Model identifier in PydanticAI format (provider:model)
        mcp_url: MCP server URL

    Yields:
        Configured PydanticAI Agent with MCP tools
    """
    # PydanticAI model format: provider:model
    model = model or os.getenv("PYDANTICAI_MODEL", "google-gla:gemini-2.0-flash")
    mcp_server = create_mcp_connection(mcp_url)

    if mcp_server:
        async with mcp_server:
            agent = Agent(
                model,
                toolsets=[mcp_server],
                output_type=DeploymentResult,
                deps_type=AgentDependencies,
                system_prompt="""You are a Qubinode infrastructure deployment assistant.

Use the available MCP tools to:
- Query RAG for relevant documentation (query_rag)
- Manage VMs via kcli (kcli_list_vms, kcli_create_vm, kcli_delete_vm)
- Trigger and monitor Airflow DAGs (trigger_dag, get_dag_status)
- Check provider availability (list_providers)
- Get lineage context (get_dag_lineage)

CONFIDENCE SCORING (per ADR-0049 Policy 1):
Always compute confidence scores based on:
- RAG similarity scores (40% weight)
- Number of relevant documents found (30% weight)
- Provider availability (20% weight)
- Similar past deployments from lineage (10% weight)

If confidence is below 0.6, request additional documentation before proceeding.
""",
            )
            yield agent
    else:
        # Fall back to agent without MCP
        yield create_deployment_agent(model)


def create_task_agent(
    model: Optional[str] = None,
) -> Agent[AgentDependencies, TaskResult]:
    """
    Create a task execution agent (simple Developer Agent role).

    This is a simplified task agent for general operations.
    For code generation tasks, use create_developer_agent instead.

    Args:
        model: Model identifier (defaults to local Granite via ollama)

    Returns:
        Configured PydanticAI Agent for task execution
    """
    model = model or os.getenv("DEVELOPER_MODEL", "ollama:granite3.3:8b")

    agent = Agent(
        model,
        output_type=TaskResult,
        deps_type=AgentDependencies,
        system_prompt="""You are a Qubinode Developer Agent for task execution.

Your responsibilities:
1. Execute specific development and configuration tasks
2. Compute and report confidence scores
3. Escalate when confidence is low or you encounter repeated failures

Per ADR-0049 Provider-First Rule:
- Always check if an Airflow provider exists for external systems
- If NO provider exists, STOP and escalate with a plan document
- Never invent pseudo-provider layers in DAGs

Report escalation_needed=True when:
- Confidence < 0.6
- Same error occurs 2+ times
- Change affects multiple DAGs
- No official Airflow provider exists
""",
    )

    @agent.output_validator
    async def validate_task_result(ctx: RunContext[AgentDependencies], output: TaskResult) -> TaskResult:
        """Auto-escalate on low confidence."""
        if output.confidence < 0.6 and not output.escalation_needed:
            output.escalation_needed = True
            output.escalation_reason = f"Low confidence: {output.confidence:.2f}"

        return output

    return agent
