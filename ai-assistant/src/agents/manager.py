"""
Manager Agent: Session orchestration and escalation decisions.

Implements ADR-0049 multi-agent coordination patterns.

The Manager Agent:
- Creates execution plans based on user intent
- Delegates to Developer Agent
- Decides when to escalate to Calling LLM
- Enforces Provider-First Rule

Per ADR-0063: PydanticAI Core Agent Orchestrator
Per ADR-0049: Multi-Agent LLM Memory Architecture
"""

import os
import logging
from typing import List, Optional

from pydantic_ai import Agent, RunContext

# Import domain models - try relative first, then absolute
try:
    from ..models.domain import (
        SessionPlan,
        EscalationRequest,
        AgentRole,
    )
    from .base import create_mcp_connection, AgentDependencies  # noqa: F401
except ImportError:
    from models.domain import (
        SessionPlan,
        EscalationRequest,
        AgentRole,
    )
    from agents.base import AgentDependencies

logger = logging.getLogger(__name__)


class ManagerDependencies(AgentDependencies):
    """Extended dependencies for Manager Agent.

    Inherits RAG and lineage services from AgentDependencies.
    """

    developer_agent_available: bool = True
    escalation_history: List[EscalationRequest] = []
    # Known providers from Airflow (for Provider-First Rule)
    known_providers: List[str] = [
        # Full package names
        "apache-airflow-providers-amazon",
        "apache-airflow-providers-google",
        "apache-airflow-providers-microsoft-azure",
        "apache-airflow-providers-ssh",
        "apache-airflow-providers-http",
        "apache-airflow-providers-postgres",
        "apache-airflow-providers-redis",
        "apache-airflow-providers-docker",
        "apache-airflow-providers-openlineage",
        # Short aliases (LLMs commonly return these)
        "ssh",
        "http",
        "postgres",
        "docker",
        "amazon",
        "google",
        "azure",
        "redis",
        "ansible",
    ]

    class Config:
        arbitrary_types_allowed = True


def create_manager_agent(
    model: Optional[str] = None,
) -> Agent[ManagerDependencies, SessionPlan]:
    """
    Create Manager Agent for session orchestration.

    The Manager Agent:
    - Creates execution plans based on user intent
    - Identifies required providers and documentation
    - Sets escalation triggers for complex operations
    - Coordinates with Developer Agent for task execution

    Args:
        model: Model identifier in PydanticAI format (provider:model)
               Examples: google-gla:gemini-2.0-flash, openai:gpt-4o

    Returns:
        Configured PydanticAI Agent with SessionPlan output type
    """
    # PydanticAI model format: provider:model (not LiteLLM format)
    # Examples: google-gla:gemini-2.0-flash, openai:gpt-4o, anthropic:claude-3-5-sonnet
    model = model or os.getenv("MANAGER_MODEL", "google-gla:gemini-2.0-flash")

    agent = Agent(
        model,
        output_type=SessionPlan,
        deps_type=ManagerDependencies,
        system_prompt="""You are a Qubinode Manager Agent for session orchestration.

Your responsibilities:
1. Analyze user intent and create execution plans
2. Identify required providers and documentation
3. Set escalation triggers for complex operations
4. Coordinate with Developer Agent for task execution

PROVIDER-FIRST RULE (ADR-0049):
Before planning any task that involves external systems:
1. Check if an official Airflow provider exists
2. If NO provider exists, set requires_external_docs=True
3. Include provider name in required_providers list

ESCALATION TRIGGERS (per ADR-0049 Policy 4):
Set escalation_triggers for:
- Any task that fails twice
- Confidence drops below 0.6
- Cross-DAG impact detected
- Missing Airflow provider
- Architecture-level changes

CONFIDENCE ESTIMATION:
Estimate confidence based on:
- Clarity of user intent
- Availability of required providers
- Complexity of task (more tasks = lower confidence)
- Past escalation history

Output a SessionPlan with:
- Clear task breakdown (planned_tasks)
- Required providers identified (required_providers)
- Escalation triggers defined (escalation_triggers)
- Confidence estimate (estimated_confidence)
""",
    )

    @agent.output_validator
    async def validate_plan(ctx: RunContext[ManagerDependencies], output: SessionPlan) -> SessionPlan:
        """
        Validate session plan and add default escalation triggers.

        Ensures complex plans have appropriate safeguards.
        """
        # Ensure escalation triggers are set for complex plans
        if len(output.planned_tasks) > 3 and not output.escalation_triggers:
            output.escalation_triggers = [
                "Any task fails twice",
                "Confidence drops below 0.6",
                "Cross-DAG impact detected",
            ]

        # Check for missing providers (fuzzy match: "ssh" matches "apache-airflow-providers-ssh")
        for provider in output.required_providers:
            provider_lower = provider.lower().strip()
            matched = any(
                provider_lower == kp.lower()
                or provider_lower in kp.lower()
                or kp.lower().endswith(f"-{provider_lower}")
                for kp in ctx.deps.known_providers
            )
            if not matched:
                if "Missing provider" not in str(output.escalation_triggers):
                    output.escalation_triggers.append(f"Missing provider: {provider} - requires documentation")
                output.requires_external_docs = True

        # Adjust confidence for escalation history
        if ctx.deps.escalation_history:
            recent_escalations = len([e for e in ctx.deps.escalation_history if e.trigger in ["repeated_failure", "confidence_deadlock"]])
            if recent_escalations > 0:
                output.estimated_confidence = max(0.3, output.estimated_confidence - (0.1 * recent_escalations))
                logger.warning(f"Reduced confidence due to {recent_escalations} recent escalations")

        return output

    return agent


async def create_escalation_request(
    trigger: str,
    context: dict,
    agent_source: AgentRole = AgentRole.MANAGER,
    failed_attempts: int = 0,
    last_error: Optional[str] = None,
) -> EscalationRequest:
    """
    Create an escalation request to be sent to Calling LLM.

    Escalation triggers per ADR-0049 Policy 4:
    - repeated_failure: Same error pattern 2+ times
    - architecture_scope: Change affects multiple DAGs
    - confidence_deadlock: Cannot achieve 0.6 threshold
    - user_request: Explicit user escalation
    - missing_provider: No official Airflow provider

    Args:
        trigger: The escalation trigger type
        context: Context about the escalation
        agent_source: Which agent initiated escalation
        failed_attempts: Number of failed attempts
        last_error: Last error message if applicable

    Returns:
        EscalationRequest to be returned to Calling LLM
    """
    # Map trigger to requested action
    action_map = {
        "repeated_failure": "Provide guidance on resolving repeated error",
        "architecture_scope": "Review architectural impact and approve changes",
        "confidence_deadlock": "Provide additional context or override confidence",
        "user_request": "Handle user request directly",
        "missing_provider": "Provide documentation or alternative approach",
    }

    return EscalationRequest(
        trigger=trigger,
        context=context,
        failed_attempts=failed_attempts,
        last_error=last_error,
        requested_action=action_map.get(trigger, "Provide guidance"),
        agent_source=agent_source,
    )
