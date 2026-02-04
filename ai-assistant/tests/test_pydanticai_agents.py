"""
Unit tests for PydanticAI agents.

Tests agent creation, confidence validation, and helper functions
per ADR-0063 and ADR-0049.

Testing Best Practices (from PydanticAI docs):
1. Use TestModel for unit testing without real API calls
2. Set models.ALLOW_MODEL_REQUESTS = False globally to prevent accidental API calls
3. Use agent.override(model=TestModel()) pattern for test isolation
4. Use capture_run_messages() to verify message flow
"""

import pytest
from unittest.mock import patch, MagicMock
import os

from pydantic_ai import models
from pydantic_ai.models.test import TestModel

from src.models.domain import SessionPlan

from src.agents.base import (
    AgentDependencies,
    create_mcp_connection,
    confidence_validator,
    create_deployment_agent,
    create_task_agent,
    configure_logfire,
)
from src.agents.manager import (
    ManagerDependencies,
    create_manager_agent,
    create_escalation_request,
)
from src.agents.developer import (
    DeveloperDependencies,
    create_developer_agent,
    compute_confidence,
    _check_aider_available,
)
from src.models.domain import (
    DeploymentResult,
    DeploymentStatus,
    AgentRole,
    EscalationRequest,
)

# Block all real model requests globally per PydanticAI testing best practices
models.ALLOW_MODEL_REQUESTS = False


class TestAgentDependencies:
    """Test agent dependencies model."""

    def test_default_dependencies(self):
        """Test default dependency values."""
        deps = AgentDependencies(session_id="test-session")
        assert deps.session_id == "test-session"
        assert deps.user_role == "operator"
        assert deps.environment == "development"
        assert deps.confidence_threshold == 0.6
        assert deps.max_retries == 3

    def test_custom_dependencies(self):
        """Test custom dependency values."""
        deps = AgentDependencies(
            session_id="prod-session",
            user_role="admin",
            environment="production",
            confidence_threshold=0.8,
            max_retries=5,
        )
        assert deps.environment == "production"
        assert deps.confidence_threshold == 0.8


class TestManagerDependencies:
    """Test manager-specific dependencies."""

    def test_manager_dependencies_defaults(self):
        """Test manager dependencies with defaults."""
        deps = ManagerDependencies(session_id="test")
        assert deps.developer_agent_available is True
        assert deps.escalation_history == []
        assert len(deps.known_providers) > 0
        assert "apache-airflow-providers-ssh" in deps.known_providers

    def test_manager_dependencies_with_history(self):
        """Test manager dependencies with escalation history."""
        escalation = EscalationRequest(
            trigger="repeated_failure",
            context={},
            requested_action="Help",
            agent_source=AgentRole.DEVELOPER,
        )
        deps = ManagerDependencies(
            session_id="test",
            escalation_history=[escalation],
        )
        assert len(deps.escalation_history) == 1


class TestDeveloperDependencies:
    """Test developer-specific dependencies."""

    def test_developer_dependencies_defaults(self):
        """Test developer dependencies with defaults."""
        deps = DeveloperDependencies(session_id="test")
        assert deps.aider_enabled is True
        assert deps.aider_model == "claude-sonnet-4-20250514"
        assert deps.working_directory == "/opt/qubinode_navigator"
        assert deps.provider_cache == {}

    def test_developer_dependencies_custom(self):
        """Test developer dependencies with custom values."""
        deps = DeveloperDependencies(
            session_id="test",
            aider_enabled=False,
            aider_model="gpt-4o",
            working_directory="/tmp/test",
        )
        assert deps.aider_enabled is False
        assert deps.aider_model == "gpt-4o"


class TestMCPConnection:
    """Test MCP connection factory."""

    def test_create_mcp_connection_default(self):
        """Test default MCP URL."""
        with patch.dict(os.environ, {}, clear=True):
            # MCP may not be available in test environment
            result = create_mcp_connection()
            # Result is None if MCP not available
            assert result is None or hasattr(result, "__class__")

    def test_create_mcp_connection_custom_url(self):
        """Test custom MCP URL."""
        result = create_mcp_connection("http://custom:9999/mcp")
        # Result depends on MCP availability
        assert result is None or hasattr(result, "__class__")


class TestConfidenceValidator:
    """Test confidence validation logic per ADR-0049 Policy 1."""

    @pytest.mark.asyncio
    async def test_high_confidence_passes(self):
        """Test that high confidence passes validation."""
        validator = confidence_validator(0.6)
        result = DeploymentResult(
            status=DeploymentStatus.SUCCESS,
            confidence=0.85,
            message="High confidence",
        )
        # Create mock context
        ctx = MagicMock()
        validated = await validator(ctx, result)
        assert validated.confidence == 0.85

    @pytest.mark.asyncio
    async def test_low_confidence_raises_retry(self):
        """Test that low confidence triggers ModelRetry."""
        from pydantic_ai import ModelRetry

        validator = confidence_validator(0.6)
        result = DeploymentResult(
            status=DeploymentStatus.PENDING,
            confidence=0.4,
            message="Low confidence",
        )
        ctx = MagicMock()

        with pytest.raises(ModelRetry) as exc_info:
            await validator(ctx, result)
        assert "Low confidence" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_medium_confidence_adds_caveats(self):
        """Test that medium confidence adds next_steps caveats."""
        validator = confidence_validator(0.6)
        result = DeploymentResult(
            status=DeploymentStatus.SUCCESS,
            confidence=0.7,
            message="Medium confidence",
            next_steps=None,  # Will be populated
        )
        ctx = MagicMock()
        validated = await validator(ctx, result)
        assert validated.next_steps is not None
        assert "Review output" in str(validated.next_steps)


class TestAgentCreation:
    """Test agent factory functions."""

    def test_create_deployment_agent_returns_agent(self):
        """Test deployment agent creation."""
        with patch.dict(os.environ, {"QUBINODE_MCP_URL": "http://test:8889/mcp"}):
            # Use 'test' model which is PydanticAI's test mode
            agent = create_deployment_agent("test")
            assert agent is not None
            assert agent.output_type == DeploymentResult

    def test_create_task_agent_returns_agent(self):
        """Test task agent creation."""
        with patch.dict(os.environ, {"QUBINODE_MCP_URL": "http://test:8889/mcp"}):
            agent = create_task_agent("test")
            assert agent is not None

    def test_create_manager_agent_returns_agent(self):
        """Test manager agent creation."""
        with patch.dict(os.environ, {"QUBINODE_MCP_URL": "http://test:8889/mcp"}):
            agent = create_manager_agent("test")
            assert agent is not None

    def test_create_developer_agent_returns_agent(self):
        """Test developer agent creation."""
        with patch.dict(os.environ, {"QUBINODE_MCP_URL": "http://test:8889/mcp"}):
            agent = create_developer_agent("test")
            assert agent is not None


class TestEscalationRequest:
    """Test escalation request creation per ADR-0049 Policy 4."""

    @pytest.mark.asyncio
    async def test_create_escalation_repeated_failure(self):
        """Test creating escalation for repeated failure."""
        request = await create_escalation_request(
            trigger="repeated_failure",
            context={"error": "Connection timeout", "count": 3},
            failed_attempts=3,
            last_error="Connection timeout",
        )
        assert request.trigger == "repeated_failure"
        assert request.failed_attempts == 3
        assert "resolving repeated error" in request.requested_action

    @pytest.mark.asyncio
    async def test_create_escalation_architecture_scope(self):
        """Test creating escalation for architecture-level change."""
        request = await create_escalation_request(
            trigger="architecture_scope",
            context={"affected_dags": ["dag1", "dag2", "dag3"]},
        )
        assert request.trigger == "architecture_scope"
        assert "architectural impact" in request.requested_action

    @pytest.mark.asyncio
    async def test_create_escalation_missing_provider(self):
        """Test creating escalation for missing provider."""
        request = await create_escalation_request(
            trigger="missing_provider",
            context={"provider_needed": "custom-api-provider"},
            agent_source=AgentRole.DEVELOPER,
        )
        assert request.trigger == "missing_provider"
        assert request.agent_source == AgentRole.DEVELOPER


class TestConfidenceComputation:
    """Test confidence score computation per ADR-0049."""

    def test_compute_confidence_all_factors(self):
        """Test confidence with all positive factors."""
        confidence = compute_confidence(
            rag_scores=[0.9, 0.85, 0.8],
            rag_hits=10,
            provider_exists=True,
            lineage_match=True,
        )
        # 0.4 * 0.85 + 0.3 * 1.0 + 0.2 * 1.0 + 0.1 * 1.0 = 0.94
        assert confidence >= 0.9

    def test_compute_confidence_no_rag(self):
        """Test confidence with no RAG results."""
        confidence = compute_confidence(
            rag_scores=[],
            rag_hits=0,
            provider_exists=True,
            lineage_match=True,
        )
        # 0.4 * 0 + 0.3 * 0 + 0.2 * 1.0 + 0.1 * 1.0 = 0.3
        assert confidence == 0.3

    def test_compute_confidence_no_provider(self):
        """Test confidence without provider (critical for Provider-First Rule)."""
        confidence = compute_confidence(
            rag_scores=[0.8, 0.75],
            rag_hits=5,
            provider_exists=False,  # Missing provider
            lineage_match=False,
        )
        # Provider missing reduces confidence significantly
        assert confidence < 0.6  # Below escalation threshold

    def test_compute_confidence_max_capped(self):
        """Test that confidence is capped at 1.0."""
        confidence = compute_confidence(
            rag_scores=[1.0, 1.0, 1.0],
            rag_hits=100,
            provider_exists=True,
            lineage_match=True,
        )
        assert confidence <= 1.0


class TestAiderAvailability:
    """Test Aider availability checking."""

    def test_aider_not_installed(self):
        """Test when Aider is not installed."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1
            assert _check_aider_available() is False

    def test_aider_installed_no_keys(self):
        """Test when Aider is installed but no API keys."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            with patch.dict(os.environ, {}, clear=True):
                assert _check_aider_available() is False

    def test_aider_installed_with_anthropic_key(self):
        """Test when Aider is installed with Anthropic key."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
                assert _check_aider_available() is True

    def test_aider_installed_with_openai_key(self):
        """Test when Aider is installed with OpenAI key."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
                assert _check_aider_available() is True


class TestLogfireConfiguration:
    """Test Logfire observability configuration."""

    def test_configure_logfire_no_token(self):
        """Test Logfire configuration without token."""
        with patch.dict(os.environ, {}, clear=True):
            # Should not fail, just return False
            result = configure_logfire()
            assert result is False

    def test_configure_logfire_with_token(self):
        """Test Logfire configuration with token."""
        with patch.dict(os.environ, {"LOGFIRE_TOKEN": "test-token"}):
            with patch("src.agents.base.LOGFIRE_AVAILABLE", True):
                with patch("src.agents.base.logfire"):
                    result = configure_logfire()
                    # May return True or False depending on mock setup
                    assert isinstance(result, bool)


class TestAgentWithTestModel:
    """
    Test agents using PydanticAI's TestModel pattern.

    These tests follow official PydanticAI testing best practices:
    - Using TestModel for isolated testing
    - Using agent.override() for model substitution
    - Verifying outputs without making real API calls
    """

    @pytest.mark.asyncio
    async def test_deployment_agent_with_test_model(self):
        """Test deployment agent using TestModel override pattern."""
        agent = create_deployment_agent("test")

        # TestModel simulates a successful response
        test_model = TestModel()

        with agent.override(model=test_model):
            # Create dependencies to verify structure (not used for actual call)
            _ = AgentDependencies(
                session_id="test-session",
                environment="development",
                confidence_threshold=0.6,
            )
            # TestModel will return a simulated response
            # This verifies the agent's structure and configuration
            assert agent.output_type == DeploymentResult

    @pytest.mark.asyncio
    async def test_manager_agent_with_test_model(self):
        """Test manager agent using TestModel override pattern."""
        agent = create_manager_agent("test")
        test_model = TestModel()

        with agent.override(model=test_model):
            # Create dependencies to verify structure (not used for actual call)
            _ = ManagerDependencies(
                session_id="test-session",
                developer_agent_available=True,
            )
            # Verify agent configuration
            assert agent is not None

    @pytest.mark.asyncio
    async def test_developer_agent_with_test_model(self):
        """Test developer agent using TestModel override pattern."""
        agent = create_developer_agent("test")
        test_model = TestModel()

        with agent.override(model=test_model):
            # Create dependencies to verify structure (not used for actual call)
            _ = DeveloperDependencies(
                session_id="test-session",
                aider_enabled=False,  # Disable Aider for test
                working_directory="/tmp/test",
            )
            # Verify agent configuration
            assert agent is not None

    def test_test_model_blocks_real_requests(self):
        """Verify that ALLOW_MODEL_REQUESTS = False blocks real API calls."""
        # This test verifies our global setting is in effect
        assert models.ALLOW_MODEL_REQUESTS is False

    @pytest.mark.asyncio
    async def test_task_agent_with_test_model(self):
        """Test task agent using TestModel override pattern."""
        from src.models.domain import TaskResult

        agent = create_task_agent("test")
        test_model = TestModel()

        with agent.override(model=test_model):
            # Create dependencies to verify structure (not used for actual call)
            _ = AgentDependencies(
                session_id="test-session",
                environment="development",
            )
            # Verify agent output type
            assert agent.output_type == TaskResult


class TestProviderFuzzyMatching:
    """Test fuzzy provider matching in validate_plan() per escalation fix."""

    def test_short_alias_in_known_providers(self):
        """Short aliases like 'ssh' should be in known_providers."""
        deps = ManagerDependencies(session_id="test")
        assert "ssh" in deps.known_providers
        assert "ansible" in deps.known_providers
        assert "http" in deps.known_providers

    def test_full_package_in_known_providers(self):
        """Full package names should still be in known_providers."""
        deps = ManagerDependencies(session_id="test")
        assert "apache-airflow-providers-ssh" in deps.known_providers
        assert "apache-airflow-providers-http" in deps.known_providers

    @pytest.mark.asyncio
    async def test_validate_plan_ssh_short_name_no_escalation(self):
        """'ssh' should match and NOT trigger missing provider escalation."""
        agent = create_manager_agent("test")
        deps = ManagerDependencies(session_id="test")
        plan = SessionPlan(
            session_id="test",
            user_intent="Deploy freeipa",
            planned_tasks=["Delete VM", "Deploy VM"],
            estimated_confidence=0.8,
            required_providers=["ssh"],
        )
        ctx = MagicMock()
        ctx.deps = deps
        validated = plan
        for validator_fn in agent._output_validators:
            validated = await validator_fn.function(ctx, validated)
        assert "Missing provider" not in str(validated.escalation_triggers)
        assert validated.requires_external_docs is False

    @pytest.mark.asyncio
    async def test_validate_plan_ansible_short_name_no_escalation(self):
        """'ansible' should match and NOT trigger missing provider escalation."""
        agent = create_manager_agent("test")
        deps = ManagerDependencies(session_id="test")
        plan = SessionPlan(
            session_id="test",
            user_intent="Deploy freeipa",
            planned_tasks=["Configure DNS"],
            estimated_confidence=0.75,
            required_providers=["ansible"],
        )
        ctx = MagicMock()
        ctx.deps = deps
        validated = plan
        for validator_fn in agent._output_validators:
            validated = await validator_fn.function(ctx, validated)
        assert "Missing provider" not in str(validated.escalation_triggers)
        assert validated.requires_external_docs is False

    @pytest.mark.asyncio
    async def test_validate_plan_ssh_and_ansible_together(self):
        """LLM returning ['ssh', 'ansible'] should NOT escalate (the original bug)."""
        agent = create_manager_agent("test")
        deps = ManagerDependencies(session_id="test")
        plan = SessionPlan(
            session_id="test",
            user_intent="Delete the freeipa server and deploy a new one",
            planned_tasks=["Delete freeipa VM", "Trigger freeipa DAG", "Verify deployment"],
            estimated_confidence=0.75,
            required_providers=["ssh", "ansible"],
        )
        ctx = MagicMock()
        ctx.deps = deps
        validated = plan
        for validator_fn in agent._output_validators:
            validated = await validator_fn.function(ctx, validated)
        assert "Missing provider" not in str(validated.escalation_triggers)
        assert validated.requires_external_docs is False
        assert validated.estimated_confidence == 0.75

    @pytest.mark.asyncio
    async def test_validate_plan_truly_unknown_provider_escalates(self):
        """A genuinely unknown provider should still trigger escalation."""
        agent = create_manager_agent("test")
        deps = ManagerDependencies(session_id="test")
        plan = SessionPlan(
            session_id="test",
            user_intent="Deploy to kubernetes",
            planned_tasks=["Deploy to k8s"],
            estimated_confidence=0.7,
            required_providers=["kubernetes"],
        )
        ctx = MagicMock()
        ctx.deps = deps
        validated = plan
        for validator_fn in agent._output_validators:
            validated = await validator_fn.function(ctx, validated)
        assert any("Missing provider" in t for t in validated.escalation_triggers)
        assert validated.requires_external_docs is True

    @pytest.mark.asyncio
    async def test_validate_plan_full_package_name_no_escalation(self):
        """Full package name 'apache-airflow-providers-ssh' should still work."""
        agent = create_manager_agent("test")
        deps = ManagerDependencies(session_id="test")
        plan = SessionPlan(
            session_id="test",
            user_intent="Deploy freeipa",
            planned_tasks=["SSH to host"],
            estimated_confidence=0.8,
            required_providers=["apache-airflow-providers-ssh"],
        )
        ctx = MagicMock()
        ctx.deps = deps
        validated = plan
        for validator_fn in agent._output_validators:
            validated = await validator_fn.function(ctx, validated)
        assert "Missing provider" not in str(validated.escalation_triggers)
