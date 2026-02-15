#!/usr/bin/env python3
"""
Qubinode AI Assistant Main Application
Based on ADR-0027: CPU-Based AI Deployment Assistant Architecture
Extended with ADR-0049/ADR-0063: PydanticAI Multi-Agent Orchestration

This module provides the main entry point for the AI assistant service,
implementing a REST API for AI inference using:
- llama.cpp and Granite-4.0-Micro (local CPU inference)
- PydanticAI Manager Agent with LiteLLM (cloud/local model routing)
"""

import logging
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional, List

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from enhanced_ai_service import create_enhanced_ai_service
from config_manager import ConfigManager
from health_monitor import HealthMonitor
from rag_ingestion_api import router as rag_router

# PydanticAI Agent imports
try:
    # Try absolute imports first (when run as module)
    from agents.manager import create_manager_agent, ManagerDependencies  # noqa: F401
    from agents.developer import create_developer_agent, DeveloperDependencies  # noqa: F401
    from agents.context import initialize_agent_context, get_agent_context  # noqa: F401
    from models.domain import SessionPlan, DeveloperTaskResult  # noqa: F401
    from services.task_executor import execute_session_plan, ExecutionResult  # noqa: F401

    PYDANTICAI_AVAILABLE = True
except ImportError:
    try:
        # Try adding src to path (when run directly)
        from pathlib import Path

        src_dir = Path(__file__).parent
        if str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))
        from agents.manager import create_manager_agent, ManagerDependencies  # noqa: F401
        from agents.developer import create_developer_agent, DeveloperDependencies  # noqa: F401
        from agents.context import initialize_agent_context, get_agent_context  # noqa: F401
        from models.domain import SessionPlan, DeveloperTaskResult  # noqa: F401
        from services.task_executor import execute_session_plan, ExecutionResult  # noqa: F401

        PYDANTICAI_AVAILABLE = True
    except ImportError as e:
        PYDANTICAI_AVAILABLE = False
        logging.warning(f"PydanticAI agents not available: {e}")

        # Dummy functions for when not available
        async def initialize_agent_context(*args, **kwargs):
            return None

        async def get_agent_context():
            return None


# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Global services
config_manager = None
ai_service = None
health_monitor = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    global config_manager, ai_service, health_monitor

    # Startup
    try:
        logger.info("Starting Qubinode AI Assistant...")

        # Initialize configuration manager
        config_manager = ConfigManager()
        await config_manager.load_config()

        # Initialize enhanced AI service
        ai_service = create_enhanced_ai_service(config_manager.config)
        await ai_service.initialize()

        # Initialize health monitor with AI service reference
        # Pass use_local_model flag so health checks know whether to check llama.cpp
        # Pass pydanticai_available so health checks fail early if orchestrator is missing
        use_local_model = config_manager.is_local_model_enabled()
        health_monitor = HealthMonitor(ai_service, use_local_model=use_local_model, pydanticai_available=PYDANTICAI_AVAILABLE)

        # Initialize PydanticAI Agent Context with RAG and lineage services
        if PYDANTICAI_AVAILABLE:
            try:
                # Get RAG service from AI service
                rag_service = getattr(ai_service, "rag_service", None)

                # Get lineage service from AI service (if available)
                lineage_service = getattr(ai_service, "lineage_service", None)

                # Initialize agent context with services and auto-load ADRs
                await initialize_agent_context(
                    rag_service=rag_service,
                    lineage_service=lineage_service,
                    auto_load_adrs=True,
                )
                logger.info("PydanticAI Agent Context initialized with RAG and lineage")
            except Exception as e:
                logger.warning(f"Agent context initialization failed: {e}")

        logger.info("Qubinode AI Assistant started successfully")

    except Exception as e:
        logger.error(f"Failed to start AI Assistant: {e}")
        sys.exit(1)

    yield

    # Shutdown
    logger.info("Shutting down Qubinode AI Assistant...")

    if ai_service:
        await ai_service.cleanup()

    logger.info("Shutdown complete")


# Initialize FastAPI app
app = FastAPI(
    title="Qubinode AI Assistant",
    description="CPU-based AI deployment assistant for infrastructure automation",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(rag_router)


class ChatRequest(BaseModel):
    """Request model for chat interactions."""

    message: str
    context: dict = {}
    max_tokens: int = 512
    temperature: float = 0.7


class ChatResponse(BaseModel):
    """Response model for chat interactions."""

    response: str
    context: dict = {}
    metadata: dict = {}


@app.get("/health")
async def health_check():
    """Health check endpoint.

    Returns:
        - 200: healthy or degraded (warnings but operational)
        - 503: unhealthy or error (service not functional)
    """
    if not health_monitor:
        raise HTTPException(status_code=503, detail="Service not ready")

    health_status = await health_monitor.get_health_status()

    # Return 200 for healthy or degraded (warnings but operational)
    # Return 503 only for unhealthy or error states
    if health_status["status"] in ("healthy", "degraded"):
        return health_status
    else:
        raise HTTPException(status_code=503, detail=health_status)


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "Qubinode AI Assistant",
        "version": "1.3.0",
        "status": "running",
        "features": {
            "rag": "Document retrieval for context-aware responses (ADRs auto-loaded)",
            "lineage": "Real-time infrastructure state from Marquez/OpenLineage",
            "orchestrator": "PydanticAI multi-agent orchestration (ADR-0049/ADR-0063)",
            "agent_context": "Shared RAG/lineage context for all agents",
        },
        "endpoints": {
            "health": "/health",
            "chat": "/chat (local Granite model)",
            "orchestrator_chat": "/orchestrator/chat (Gemini/LiteLLM with RAG context)",
            "orchestrator_status": "/orchestrator/status",
            "orchestrator_context": "/orchestrator/context (view agent context)",
            "orchestrator_context_query": "POST /orchestrator/context/query (query RAG/lineage)",
            "orchestrator_context_reload": "POST /orchestrator/context/reload (reload ADRs)",
            "orchestrator_projects": "/orchestrator/projects (list source projects - ADR-0066)",
            "orchestrator_dags": "/orchestrator/dags (list/search/validate DAGs - ADR-0066)",
            "orchestrator_dags_search": "POST /orchestrator/dags/search (find DAG for task)",
            "orchestrator_dags_validate": "POST /orchestrator/dags/validate (validate DAG)",
            "orchestrator_dags_generate": "POST /orchestrator/dags/generate (create new DAG)",
            "orchestrator_dags_approve": "POST /orchestrator/dags/approve (deploy DAG)",
            "diagnostics": "/diagnostics",
            "diagnostics_tools": "/diagnostics/tools",
            "specific_tool": "/diagnostics/tool/{tool_name}",
            "lineage": "/lineage",
            "lineage_job": "/lineage/job/{job_name}",
            "docs": "/docs",
        },
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Main chat endpoint for AI interactions."""
    if not ai_service:
        raise HTTPException(status_code=503, detail="AI service not available")

    try:
        response = await ai_service.process_message(
            message=request.message,
            context=request.context,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )

        return ChatResponse(
            response=response["text"],
            context=response.get("context", {}),
            metadata=response.get("metadata", {}),
        )

    except Exception as e:
        logger.error(f"Chat processing error: {e}")
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")


@app.post("/diagnostics")
async def run_diagnostics(request: dict):
    """Run system diagnostics and provide AI-powered analysis."""
    if not ai_service:
        raise HTTPException(status_code=503, detail="AI service not available")

    try:
        diagnostics_result = await ai_service.run_diagnostics(request)
        return diagnostics_result

    except Exception as e:
        logger.error(f"Diagnostics error: {e}")
        raise HTTPException(status_code=500, detail=f"Diagnostics error: {str(e)}")


@app.get("/diagnostics/tools")
async def list_diagnostic_tools():
    """List all available diagnostic tools."""
    if not ai_service:
        raise HTTPException(status_code=503, detail="AI service not available")

    try:
        tools = ai_service.get_available_diagnostic_tools()
        return {
            "available_tools": tools,
            "total_tools": len(tools),
            "timestamp": time.time(),
        }

    except Exception as e:
        logger.error(f"Tools listing error: {e}")
        raise HTTPException(status_code=500, detail=f"Tools listing error: {str(e)}")


@app.post("/diagnostics/tool/{tool_name}")
async def run_specific_diagnostic_tool(tool_name: str, request: dict = None):
    """Run a specific diagnostic tool by name."""
    if not ai_service:
        raise HTTPException(status_code=503, detail="AI service not available")

    try:
        request_data = request or {}
        result = await ai_service.run_specific_diagnostic_tool(tool_name, **request_data)
        return result

    except Exception as e:
        logger.error(f"Specific tool error: {e}")
        raise HTTPException(status_code=500, detail=f"Tool execution error: {str(e)}")


@app.get("/model/info")
async def get_model_info():
    """Get current model information."""
    if not ai_service:
        raise HTTPException(status_code=503, detail="AI service not available")

    try:
        model_info = ai_service.get_model_info()
        return {"model_info": model_info, "timestamp": time.time()}
    except Exception as e:
        logger.error(f"Model info error: {e}")
        raise HTTPException(status_code=500, detail=f"Model info error: {str(e)}")


@app.get("/model/hardware")
async def get_hardware_info():
    """Get hardware capabilities and recommendations."""
    if not ai_service:
        raise HTTPException(status_code=503, detail="AI service not available")

    try:
        hardware_info = ai_service.get_hardware_info()
        return {"hardware_info": hardware_info, "timestamp": time.time()}
    except Exception as e:
        logger.error(f"Hardware info error: {e}")
        raise HTTPException(status_code=500, detail=f"Hardware info error: {str(e)}")


@app.get("/config")
async def get_config():
    """Get current configuration (sanitized)."""
    if not config_manager:
        raise HTTPException(status_code=503, detail="Config service not available")

    return config_manager.get_sanitized_config()


# =============================================================================
# RAG Query Endpoints (Document Search)
# =============================================================================


class QueryRequest(BaseModel):
    """Request model for RAG document query"""

    query: str
    max_results: int = 5


class QueryResult(BaseModel):
    """Single query result"""

    content: str
    score: float
    source: str
    title: str = ""


class QueryResponse(BaseModel):
    """Response model for RAG document query"""

    results: list = []
    query: str = ""
    total_results: int = 0


@app.post("/api/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """Search documentation using RAG.

    This endpoint enables MCP tools to search the knowledge base
    for relevant documentation about infrastructure, deployment, etc.

    Args:
        query: Search query string
        max_results: Maximum number of results to return (default: 5)

    Returns:
        List of relevant document chunks with scores and sources
    """
    if not ai_service:
        raise HTTPException(status_code=503, detail="AI service not available")

    try:
        # Access the RAG service from the AI service
        if not hasattr(ai_service, "rag_service") or ai_service.rag_service is None:
            # Return empty results if RAG is not available
            logger.warning("RAG service not available for query")
            return QueryResponse(results=[], query=request.query, total_results=0)

        # Search documents using RAG service
        results = await ai_service.rag_service.search_documents(query=request.query, n_results=request.max_results)

        # Format results for response
        formatted_results = []
        for result in results:
            formatted_results.append(
                {
                    "content": result.content,
                    "score": result.score,
                    "source": result.source_file,
                    "title": result.title,
                }
            )

        logger.info(f"RAG query '{request.query[:50]}...' returned {len(formatted_results)} results")
        return QueryResponse(results=formatted_results, query=request.query, total_results=len(formatted_results))

    except Exception as e:
        logger.error(f"RAG query error: {e}")
        raise HTTPException(status_code=500, detail=f"Query error: {str(e)}")


# =============================================================================
# Status Endpoints (Project and Service Status)
# =============================================================================


@app.get("/api/status")
async def get_project_status():
    """Get comprehensive project status for MCP tools.

    Returns current status of:
    - AI Assistant service
    - Airflow/DAG execution
    - Virtual machines
    - System metrics

    This endpoint is called by the MCP get_project_status tool.
    """
    if not health_monitor:
        raise HTTPException(status_code=503, detail="Health monitor not available")

    try:
        # Get health status
        health = await health_monitor.get_health_status()

        # Get lineage summary if available
        lineage_summary = {}
        if ai_service:
            try:
                lineage_summary = await ai_service.get_lineage_summary()
            except Exception:
                lineage_summary = {"available": False}

        # Build comprehensive status
        status = {
            "ai_status": health.get("status", "unknown"),
            "uptime_seconds": health.get("uptime_seconds", 0),
            "airflow_status": "connected" if lineage_summary.get("available") else "disconnected",
            "vm_count": lineage_summary.get("job_stats", {}).get("total", 0),
            "metrics": {
                "cpu": f"{health.get('system', {}).get('metrics', {}).get('cpu_percent', 0):.1f}%",
                "memory": f"{health.get('system', {}).get('metrics', {}).get('memory_percent', 0):.1f}%",
                "disk": f"{health.get('system', {}).get('metrics', {}).get('disk_percent', 0):.1f}%",
            },
            "recent_failures": lineage_summary.get("recent_failures", []),
            "job_stats": lineage_summary.get("job_stats", {}),
            "timestamp": time.time(),
        }

        return status

    except Exception as e:
        logger.error(f"Status endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"Status error: {str(e)}")


# =============================================================================
# Lineage Endpoints (Marquez/OpenLineage Integration)
# =============================================================================


@app.get("/lineage")
async def get_lineage_summary():
    """Get infrastructure lineage summary from Marquez.

    Returns current state of DAG runs, failures, and deployment history.
    This data is also used to enhance AI responses with real-time context.
    """
    if not ai_service:
        raise HTTPException(status_code=503, detail="AI service not available")

    try:
        summary = await ai_service.get_lineage_summary()
        return {"lineage": summary, "timestamp": time.time()}
    except Exception as e:
        logger.error(f"Lineage summary error: {e}")
        raise HTTPException(status_code=500, detail=f"Lineage error: {str(e)}")


@app.get("/lineage/job/{job_name}")
async def get_job_lineage(job_name: str):
    """Get detailed lineage for a specific job/DAG.

    Args:
        job_name: The name of the job/DAG (e.g., 'freeipa_deployment', 'dns_management')
    """
    if not ai_service:
        raise HTTPException(status_code=503, detail="AI service not available")

    try:
        job_info = await ai_service.get_job_lineage(job_name)
        if job_info is None:
            raise HTTPException(status_code=404, detail=f"Job '{job_name}' not found")
        return {"job": job_info, "timestamp": time.time()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Job lineage error for {job_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Lineage error: {str(e)}")


# =============================================================================
# Orchestrator Endpoints (PydanticAI Multi-Agent - ADR-0049/ADR-0063)
# =============================================================================


class OrchestratorRequest(BaseModel):
    """Request model for orchestrator chat."""

    message: str = Field(..., description="User message/task to process")
    session_id: Optional[str] = Field(None, description="Session ID for conversation continuity")
    user_role: str = Field(default="operator", description="User role for permissions")
    environment: str = Field(default="development", description="Target environment")
    execute_tasks: bool = Field(default=True, description="Execute planned tasks via Developer Agent")
    working_directory: str = Field(default="/opt/qubinode_navigator", description="Working directory for code changes")


class OrchestratorResponse(BaseModel):
    """Response model for orchestrator chat."""

    session_id: str
    model_used: str
    plan: Optional[dict] = None
    response_text: str
    confidence: float
    escalation_needed: bool = False
    escalation_reason: Optional[str] = None
    planned_tasks: List[str] = []
    required_providers: List[str] = []
    timestamp: float
    # Execution results (when execute_tasks=True)
    execution_performed: bool = False
    execution_success: bool = False
    tasks_executed: int = 0
    tasks_succeeded: int = 0
    tasks_failed: int = 0
    tasks_escalated: int = 0
    execution_confidence: float = 0.0
    execution_log_file: Optional[str] = None
    execution_summary: Optional[str] = None
    code_changes: List[dict] = []


async def _try_intent_fast_path(message: str) -> Optional[OrchestratorResponse]:
    """
    Try to handle the request via the deterministic intent parser.
    Returns OrchestratorResponse if handled, None to fall through to agents.
    """
    try:
        import sys as _sys
        if "/app" not in _sys.path:
            _sys.path.insert(0, "/app")
        from intent_parser import IntentParser, IntentCategory

        parser = IntentParser()
        parsed = parser.classify(message)

        logger.info(f"Intent fast path: category={parsed.category.value} confidence={parsed.confidence} input='{message[:80]}'")

        # Only fast-path for high-confidence, actionable intents
        FAST_PATH_CATEGORIES = {
            IntentCategory.DAG_TRIGGER,
            IntentCategory.DAG_LIST,
            IntentCategory.DAG_INFO,
            IntentCategory.VM_LIST,
            IntentCategory.VM_INFO,
            IntentCategory.VM_CREATE,
            IntentCategory.VM_DELETE,
            IntentCategory.VM_PREFLIGHT,
            IntentCategory.SYSTEM_STATUS,
            IntentCategory.SYSTEM_INFO,
            IntentCategory.RAG_QUERY,
            IntentCategory.RAG_STATS,
        }

        if parsed.confidence < 0.5 or parsed.category not in FAST_PATH_CATEGORIES:
            return None  # Fall through to full orchestrator

        # Run VM SSH preflight for DAG triggers (auto-fix SSH key issues)
        preflight_report = ""
        if parsed.category == IntentCategory.DAG_TRIGGER:
            try:
                from intent_parser.vm_ssh_preflight import (
                    run_vm_ssh_preflight, get_vm_for_dag,
                )
                dag_id = (parsed.entities or {}).get("dag_id", "")
                conf = parsed.parameters or {}
                vm_info = get_vm_for_dag(dag_id, conf)
                if vm_info:
                    vm_name, ssh_user = vm_info
                    vm_result = await run_vm_ssh_preflight(vm_name, ssh_user)
                    preflight_report = vm_result.format_report()
                    if preflight_report:
                        logger.info("VM SSH preflight: %s", preflight_report)
            except ImportError:
                logger.debug("VM SSH preflight not available")
            except Exception as e:
                logger.warning("VM SSH preflight failed: %s", e)

        # Execute via intent parser
        result = await parser.process(message)

        response_text = result.output if result.success else f"Error: {result.error}"
        if preflight_report:
            response_text = f"{preflight_report}\n\n{response_text}"

        return OrchestratorResponse(
            session_id=str(uuid.uuid4()),
            model_used="intent-parser (deterministic)",
            plan={
                "session_id": "intent-fast-path",
                "user_intent": message,
                "planned_tasks": [f"Execute {parsed.category.value}: {message}"],
                "estimated_confidence": parsed.confidence,
                "requires_external_docs": False,
                "required_providers": [],
                "escalation_triggers": [],
            },
            response_text=response_text,
            confidence=parsed.confidence,
            escalation_needed=not result.success,
            escalation_reason=result.error if not result.success else None,
            planned_tasks=[f"Execute {parsed.category.value}: {message}"],
            required_providers=[],
            timestamp=time.time(),
            execution_performed=True,
            execution_success=result.success,
            tasks_executed=1,
            tasks_succeeded=1 if result.success else 0,
            tasks_failed=0 if result.success else 1,
            tasks_escalated=0,
            execution_confidence=parsed.confidence,
            execution_log_file=None,
            execution_summary=result.output,
            code_changes=[],
        )
    except ImportError:
        logger.debug("Intent parser not available, falling through to agents")
        return None
    except Exception as e:
        logger.warning(f"Intent parser fast path failed: {e}, falling through to agents")
        return None


@app.post("/orchestrator/chat", response_model=OrchestratorResponse)
async def orchestrator_chat(request: OrchestratorRequest):
    """
    Chat with the PydanticAI Manager Agent (orchestrator).

    This endpoint implements the three-tier agent architecture (ADR-0049):
    1. Manager Agent: Analyzes intent and creates execution plans
    2. Developer Agent: Executes each planned task (when execute_tasks=True)
    3. Calling LLM: Handles escalations when confidence is low

    Features:
    - Analyze user intent and create execution plans
    - Query RAG for relevant documentation context
    - Query lineage for execution history
    - Identify required Airflow providers
    - Execute planned tasks via Developer Agent
    - Log the entire coding process to a reviewable file
    - Handle escalations for complex operations

    Request Options:
    - execute_tasks (default: True): Execute planned tasks via Developer Agent
    - working_directory: Directory for code changes

    Response includes:
    - Session plan from Manager Agent
    - Execution results (tasks succeeded/failed/escalated)
    - Path to execution log file for review
    - Code changes made during execution

    Models supported via LiteLLM:
    - gemini/gemini-2.0-flash (default, fast and cheap)
    - openrouter/anthropic/claude-3.5-sonnet
    - ollama/granite3.3:8b (local)
    - And 100+ more providers

    Set MANAGER_MODEL env var or GEMINI_API_KEY to configure.
    """
    if not PYDANTICAI_AVAILABLE:
        raise HTTPException(status_code=503, detail="PydanticAI agents not available. Install with: pip install pydantic-ai")

    # Check for API key
    has_gemini = bool(os.getenv("GEMINI_API_KEY"))
    has_openrouter = bool(os.getenv("OPENROUTER_API_KEY"))
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))
    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_ollama = bool(os.getenv("OLLAMA_BASE_URL"))

    if not any([has_gemini, has_openrouter, has_anthropic, has_openai, has_ollama]):
        raise HTTPException(status_code=503, detail="No LLM API key configured. Set one of: GEMINI_API_KEY, OPENROUTER_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY, or OLLAMA_BASE_URL")

    # Fast path: try intent parser for deterministic routing
    intent_result = await _try_intent_fast_path(request.message)
    if intent_result is not None:
        return intent_result

    try:
        # Create or use existing session
        session_id = request.session_id or str(uuid.uuid4())

        # Run RAG pre-flight checks with auto-fix
        rag_preflight_report = ""
        try:
            from intent_parser.rag_preflight import run_rag_preflight
            rag_preflight_result = await run_rag_preflight()
            rag_preflight_report = rag_preflight_result.format_report()
        except ImportError:
            logger.debug("RAG preflight not available")
        except Exception as e:
            logger.warning(f"RAG preflight failed: {e}")

        # Create Manager Agent
        agent = create_manager_agent()
        model_name = str(agent.model)

        logger.info(f"Orchestrator chat - Session: {session_id}, Model: {model_name}")

        # Get RAG and lineage context from AgentContextManager
        agent_ctx = await get_agent_context()
        rag_context = []
        rag_sources = []
        lineage_context = {}

        dag_matches = []
        if agent_ctx:
            try:
                # Query RAG, lineage, and DAGs for relevant context
                ctx = await agent_ctx.get_context_for_task(request.message, include_dags=True)
                rag_context = ctx.get("rag", {}).get("contexts", [])
                rag_sources = ctx.get("rag", {}).get("sources", [])
                lineage_context = ctx.get("lineage", {})
                dag_matches = ctx.get("dags", {}).get("matches", [])
                logger.info(f"RAG returned {len(rag_context)} contexts, found {len(dag_matches)} matching DAGs")
            except Exception as e:
                logger.warning(f"Context retrieval failed: {e}")

        # Build enhanced message with RAG + DAG context
        enhanced_message = request.message

        context_parts = []
        if rag_context:
            context_text = "\n\n".join(rag_context[:5])  # Top 5 contexts
            context_parts.append(f"## Relevant Documentation (from RAG):\n{context_text}\n\n## Sources: {', '.join(rag_sources[:5])}")

        if dag_matches:
            dag_text = "\n".join([f"- **{dag['dag_id']}**: {dag.get('description', 'No description')} (tags: {', '.join(dag.get('tags', []))})" for dag in dag_matches[:3]])
            context_parts.append(
                f"""## Available DAGs for this task:
{dag_text}

**To execute a DAG, use:** `airflow dags trigger <dag_id> --conf '{{"param": "value"}}'`
Or call the MCP tool: `trigger_dag(dag_id="<dag_id>", conf={{...}})`"""
            )

        if context_parts:
            enhanced_message = f"""## User Request:
{request.message}

{"".join(context_parts)}
"""

        # Create dependencies with RAG/lineage context
        deps = ManagerDependencies(
            session_id=session_id,
            user_role=request.user_role,
            environment=request.environment,
            rag_service=agent_ctx.rag_service if agent_ctx else None,
            lineage_service=agent_ctx.lineage_service if agent_ctx else None,
            rag_context=rag_context,
            rag_sources=rag_sources,
            lineage_context=lineage_context,
        )

        # Run the agent with enhanced message
        result = await agent.run(enhanced_message, deps=deps)
        plan: SessionPlan = result.output

        # Build response text
        response_parts = ["## Session Plan\n"]
        response_parts.append(f"**Intent:** {plan.user_intent}\n")
        response_parts.append(f"**Confidence:** {plan.estimated_confidence:.0%}\n")

        if plan.planned_tasks:
            response_parts.append("\n### Planned Tasks:")
            for i, task in enumerate(plan.planned_tasks, 1):
                response_parts.append(f"{i}. {task}")

        if plan.required_providers:
            response_parts.append("\n### Required Providers:")
            for provider in plan.required_providers:
                response_parts.append(f"- {provider}")

        if plan.escalation_triggers:
            response_parts.append("\n### Escalation Triggers:")
            for trigger in plan.escalation_triggers:
                response_parts.append(f"- {trigger}")

        if plan.requires_external_docs:
            response_parts.append("\n**Note:** This task requires external documentation.")

        response_text = "\n".join(response_parts)

        # Initialize execution result fields
        execution_performed = False
        execution_success = False
        tasks_executed = 0
        tasks_succeeded = 0
        tasks_failed = 0
        tasks_escalated = 0
        execution_confidence = 0.0
        execution_log_file = None
        execution_summary = None
        code_changes = []
        escalation_needed = plan.estimated_confidence < 0.6
        escalation_reason = "Low confidence - requires additional context" if escalation_needed else None

        # Execute planned tasks via Developer Agent if requested
        if request.execute_tasks and plan.planned_tasks and not escalation_needed:
            logger.info(f"Executing {len(plan.planned_tasks)} planned tasks via Developer Agent...")
            response_parts.append("\n---\n")
            response_parts.append("## Task Execution\n")

            try:
                exec_result = await execute_session_plan(
                    session_id=session_id,
                    plan=plan,
                    rag_service=agent_ctx.rag_service if agent_ctx else None,
                    lineage_service=agent_ctx.lineage_service if agent_ctx else None,
                    rag_context=rag_context,
                    lineage_context=lineage_context,
                    working_directory=request.working_directory,
                )

                execution_performed = True
                execution_success = exec_result.success
                tasks_executed = exec_result.tasks_executed
                tasks_succeeded = exec_result.tasks_succeeded
                tasks_failed = exec_result.tasks_failed
                tasks_escalated = exec_result.tasks_escalated
                execution_confidence = exec_result.overall_confidence
                execution_log_file = exec_result.log_file_path
                execution_summary = exec_result.summary
                code_changes = exec_result.code_changes

                # Update escalation status based on execution
                if exec_result.escalation_needed:
                    escalation_needed = True
                    escalation_reason = "Tasks require escalation - see execution log for details"

                # Add execution summary to response
                response_parts.append(f"**Status:** {'Success' if execution_success else 'Partial/Failed'}\n")
                response_parts.append(f"**Tasks Executed:** {tasks_executed}\n")
                response_parts.append(f"**Tasks Succeeded:** {tasks_succeeded}\n")
                if tasks_failed > 0:
                    response_parts.append(f"**Tasks Failed:** {tasks_failed}\n")
                if tasks_escalated > 0:
                    response_parts.append(f"**Tasks Escalated:** {tasks_escalated}\n")
                response_parts.append(f"**Execution Confidence:** {execution_confidence:.0%}\n")
                response_parts.append(f"\n**Execution Log:** `{execution_log_file}`\n")
                response_parts.append("*Review the log file for detailed execution information.*")

                if code_changes:
                    response_parts.append("\n### Code Changes:")
                    for change in code_changes[:5]:  # Show top 5
                        response_parts.append(f"- {change.get('task', 'Unknown')[:60]}...")

                logger.info(f"Task execution completed: {tasks_succeeded}/{tasks_executed} succeeded")

            except Exception as exec_error:
                logger.error(f"Task execution failed: {exec_error}", exc_info=True)
                execution_performed = True
                execution_success = False
                response_parts.append(f"**Execution Error:** {str(exec_error)}\n")
                escalation_needed = True
                escalation_reason = f"Task execution failed: {str(exec_error)}"

        elif request.execute_tasks and not plan.planned_tasks:
            response_parts.append("\n*No tasks to execute.*")
        elif request.execute_tasks and escalation_needed:
            response_parts.append("\n*Task execution skipped due to low confidence. Escalation required.*")

        response_text = "\n".join(response_parts)

        if rag_preflight_report:
            response_text = f"{rag_preflight_report}\n\n{response_text}"

        return OrchestratorResponse(
            session_id=session_id,
            model_used=model_name,
            plan=plan.model_dump(),
            response_text=response_text,
            confidence=plan.estimated_confidence,
            escalation_needed=escalation_needed,
            escalation_reason=escalation_reason,
            planned_tasks=plan.planned_tasks,
            required_providers=plan.required_providers,
            timestamp=time.time(),
            execution_performed=execution_performed,
            execution_success=execution_success,
            tasks_executed=tasks_executed,
            tasks_succeeded=tasks_succeeded,
            tasks_failed=tasks_failed,
            tasks_escalated=tasks_escalated,
            execution_confidence=execution_confidence,
            execution_log_file=execution_log_file,
            execution_summary=execution_summary,
            code_changes=code_changes,
        )

    except Exception as e:
        logger.error(f"Orchestrator chat error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Orchestrator error: {str(e)}")


@app.get("/orchestrator/status")
async def orchestrator_status():
    """Get orchestrator (PydanticAI) status and configuration."""
    status = {
        "available": PYDANTICAI_AVAILABLE,
        "timestamp": time.time(),
    }

    if PYDANTICAI_AVAILABLE:
        # PydanticAI model format: provider:model
        # Examples: google-gla:gemini-2.0-flash, openai:gpt-4o, anthropic:claude-3-5-sonnet
        status["models"] = {
            "manager": os.getenv("MANAGER_MODEL", "google-gla:gemini-2.0-flash"),
            "developer": os.getenv("DEVELOPER_MODEL", "google-gla:gemini-2.0-flash"),
            "deployment": os.getenv("PYDANTICAI_MODEL", "google-gla:gemini-2.0-flash"),
        }
        status["api_keys_configured"] = {
            "gemini": bool(os.getenv("GEMINI_API_KEY")),
            "openrouter": bool(os.getenv("OPENROUTER_API_KEY")),
            "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
            "openai": bool(os.getenv("OPENAI_API_KEY")),
            "ollama": bool(os.getenv("OLLAMA_BASE_URL")),
        }
        status["mcp_url"] = os.getenv("QUBINODE_MCP_URL", "http://localhost:8889/sse")
        status["model_format_note"] = "PydanticAI uses provider:model format (e.g., google-gla:gemini-2.0-flash)"

        # Add agent context status
        agent_ctx = await get_agent_context()
        if agent_ctx:
            status["agent_context"] = agent_ctx.get_status()

    return status


# =============================================================================
# Agent Context Management Endpoints
# =============================================================================


@app.get("/orchestrator/context")
async def get_orchestrator_context():
    """
    Get the current agent context status.

    Shows whether RAG and lineage services are available,
    and whether ADRs have been loaded into RAG.
    """
    agent_ctx = await get_agent_context()
    if not agent_ctx:
        return {
            "available": False,
            "message": "Agent context not initialized",
        }

    return {
        "available": True,
        "status": agent_ctx.get_status(),
        "timestamp": time.time(),
    }


class ContextQueryRequest(BaseModel):
    """Request for querying agent context."""

    query: str
    top_k: int = 5
    include_lineage: bool = True


@app.post("/orchestrator/context/query")
async def query_orchestrator_context(request: ContextQueryRequest):
    """
    Query the agent context for relevant documentation.

    This endpoint allows users and LLMs to:
    - Search RAG for documentation
    - Get lineage execution history
    - Understand what context the orchestrator has

    Args:
        query: Search query for RAG
        top_k: Maximum results to return
        include_lineage: Whether to include lineage data
    """
    agent_ctx = await get_agent_context()
    if not agent_ctx:
        raise HTTPException(status_code=503, detail="Agent context not initialized")

    try:
        context = await agent_ctx.get_context_for_task(
            request.query,
            include_lineage=request.include_lineage,
        )

        return {
            "query": request.query,
            "rag": context.get("rag", {}),
            "lineage": context.get("lineage", {}),
            "timestamp": time.time(),
        }

    except Exception as e:
        logger.error(f"Context query error: {e}")
        raise HTTPException(status_code=500, detail=f"Query error: {str(e)}")


@app.post("/orchestrator/context/reload")
async def reload_orchestrator_context():
    """
    Reload ADRs and refresh the agent context.

    Use this after adding new ADRs or updating documentation.
    """
    agent_ctx = await get_agent_context()
    if not agent_ctx:
        raise HTTPException(status_code=503, detail="Agent context not initialized")

    try:
        # Force reload of ADRs
        agent_ctx.adrs_loaded = False
        await agent_ctx._ensure_adrs_loaded()

        return {
            "success": True,
            "message": "Agent context reloaded",
            "status": agent_ctx.get_status(),
            "timestamp": time.time(),
        }

    except Exception as e:
        logger.error(f"Context reload error: {e}")
        raise HTTPException(status_code=500, detail=f"Reload error: {str(e)}")


# =============================================================================
# Project Registry Endpoints (ADR-0066)
# =============================================================================

# Import project registry
try:
    from project_registry import (
        get_project_registry,
        find_project_for_task,
        analyze_external_project,
        ProjectCapability,  # noqa: F401
    )

    PROJECT_REGISTRY_AVAILABLE = True
except ImportError:
    PROJECT_REGISTRY_AVAILABLE = False
    logger.warning("Project registry not available")


class ProjectQueryRequest(BaseModel):
    """Request for finding projects for a task."""

    task_description: str


class ProjectAnalyzeRequest(BaseModel):
    """Request for analyzing an external project."""

    path: str


class ProjectRegisterRequest(BaseModel):
    """Request for registering a new project."""

    name: str
    path: str
    git_url: Optional[str] = None
    description: str = ""
    capabilities: List[str] = []
    entry_points: dict = {}
    config_paths: dict = {}


@app.get("/orchestrator/projects")
async def list_projects():
    """
    List all registered projects.

    Returns projects with their availability status and capabilities.
    Per ADR-0066: Project-Aware DAG Creation.
    """
    if not PROJECT_REGISTRY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Project registry not available")

    registry = await get_project_registry()
    projects = registry.get_all_projects()

    return {
        "projects": [
            {
                "name": p.name,
                "path": p.path,
                "git_url": p.git_url,
                "description": p.description,
                "capabilities": [c.value for c in p.capabilities],
                "is_available": p.is_available,
                "entry_points": list(p.entry_points.keys()),
            }
            for p in projects
        ],
        "total": len(projects),
        "available": len([p for p in projects if p.is_available]),
        "timestamp": time.time(),
    }


@app.get("/orchestrator/projects/{name}")
async def get_project(name: str):
    """
    Get details about a specific project.

    Returns full project information including entry points and config paths.
    """
    if not PROJECT_REGISTRY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Project registry not available")

    registry = await get_project_registry()
    project = registry.get_project(name)

    if not project:
        raise HTTPException(status_code=404, detail=f"Project not found: {name}")

    return {
        "name": project.name,
        "path": project.path,
        "git_url": project.git_url,
        "description": project.description,
        "capabilities": [c.value for c in project.capabilities],
        "is_available": project.is_available,
        "entry_points": {
            ep_name: {
                "command": ep.command,
                "description": ep.description,
                "required_params": ep.required_params,
                "optional_params": ep.optional_params,
            }
            for ep_name, ep in project.entry_points.items()
        },
        "config_paths": project.config_paths,
        "timestamp": time.time(),
    }


@app.post("/orchestrator/projects/find")
async def find_projects_for_task(request: ProjectQueryRequest):
    """
    Find projects that can handle a specific task.

    Uses capability matching to find relevant projects.
    Per ADR-0066: Project-Aware DAG Creation.
    """
    if not PROJECT_REGISTRY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Project registry not available")

    projects = await find_project_for_task(request.task_description)

    return {
        "task_description": request.task_description,
        "matching_projects": [
            {
                "name": p.name,
                "path": p.path,
                "capabilities": [c.value for c in p.capabilities],
                "is_available": p.is_available,
                "entry_points": list(p.entry_points.keys()),
            }
            for p in projects
        ],
        "total_matches": len(projects),
        "timestamp": time.time(),
    }


@app.post("/orchestrator/projects/analyze")
async def analyze_project(request: ProjectAnalyzeRequest):
    """
    Analyze an external project directory.

    Discovers entry points, configuration files, dependencies,
    and provides suggestions for DAG creation.
    Per ADR-0066: External Project Handling.
    """
    if not PROJECT_REGISTRY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Project registry not available")

    analysis = await analyze_external_project(request.path)

    return {
        "path": request.path,
        "analysis": analysis,
        "timestamp": time.time(),
    }


@app.post("/orchestrator/projects/register")
async def register_project(request: ProjectRegisterRequest):
    """
    Register a new project in the registry.

    The project will be available for task matching after registration.
    """
    if not PROJECT_REGISTRY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Project registry not available")

    registry = await get_project_registry()

    config = {
        "path": request.path,
        "git_url": request.git_url,
        "description": request.description,
        "capabilities": request.capabilities,
        "entry_points": request.entry_points,
        "config_paths": request.config_paths,
    }

    try:
        project = await registry.register_project(request.name, config)
        return {
            "success": True,
            "name": project.name,
            "is_available": project.is_available,
            "message": f"Project '{request.name}' registered successfully",
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.error(f"Failed to register project: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to register project: {str(e)}")


@app.post("/orchestrator/projects/{name}/ensure")
async def ensure_project_available(name: str, clone_if_missing: bool = False):
    """
    Ensure a project is available, optionally cloning if missing.

    Args:
        name: Project name
        clone_if_missing: Whether to clone from git if not present
    """
    if not PROJECT_REGISTRY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Project registry not available")

    registry = await get_project_registry()

    try:
        project = await registry.ensure_project_available(
            name,
            clone_if_missing=clone_if_missing,
        )
        return {
            "name": project.name,
            "path": project.path,
            "is_available": project.is_available,
            "message": "Project is available" if project.is_available else "Project not available",
            "timestamp": time.time(),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to ensure project: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to ensure project: {str(e)}")


# =============================================================================
# DAG Validation Endpoints (ADR-0066 Phase 2)
# =============================================================================

# Import DAG validator
try:
    from dag_validator import (
        get_dag_validator,
        find_or_create_dag,
        DAGCreationRequest,
    )

    DAG_VALIDATOR_AVAILABLE = True
except ImportError:
    DAG_VALIDATOR_AVAILABLE = False
    logger.warning("DAG validator not available")


class DAGSearchRequest(BaseModel):
    """Request for searching DAGs for a task."""

    task_description: str
    params: dict = {}


class DAGValidateRequest(BaseModel):
    """Request for validating a specific DAG."""

    dag_id: str
    params: dict = {}


class DAGCreateRequest(BaseModel):
    """Request for creating a new DAG."""

    dag_id: str
    description: str
    task_description: str
    source_project: Optional[str] = None
    params: dict = {}


class DAGApproveRequest(BaseModel):
    """Request for approving and deploying a generated DAG."""

    dag_id: str
    dag_code: str
    file_path: str


@app.get("/orchestrator/dags")
async def list_dags():
    """
    List all discovered DAGs from the Airflow dags folder.

    Returns DAG metadata including description, tags, and params.
    Per ADR-0066: DAG Validation and Creation.
    """
    if not DAG_VALIDATOR_AVAILABLE:
        raise HTTPException(status_code=503, detail="DAG validator not available")

    validator = await get_dag_validator()
    dags = await validator.discover_dags()

    return {
        "dags": [
            {
                "dag_id": d.dag_id,
                "file_path": d.file_path,
                "description": d.description,
                "schedule": d.schedule,
                "tags": d.tags,
                "params": d.params,
            }
            for d in dags
        ],
        "total": len(dags),
        "timestamp": time.time(),
    }


@app.post("/orchestrator/dags/search")
async def search_dags(request: DAGSearchRequest):
    """
    Search for DAGs that can fulfill a task.

    Uses intent matching to find suitable DAGs.
    Returns best match and recommendations.
    Per ADR-0066: DAG Validation and Creation.
    """
    if not DAG_VALIDATOR_AVAILABLE:
        raise HTTPException(status_code=503, detail="DAG validator not available")

    result = await find_or_create_dag(
        request.task_description,
        request.params,
    )

    return {
        "task_description": request.task_description,
        **result,
        "timestamp": time.time(),
    }


@app.post("/orchestrator/dags/validate")
async def validate_dag(request: DAGValidateRequest):
    """
    Validate a specific DAG can fulfill task requirements.

    Checks:
    - DAG exists and is active
    - Required parameters are provided
    - Domain-specific pre-flight checks pass

    Per ADR-0066: DAG Validation and Creation.
    """
    if not DAG_VALIDATOR_AVAILABLE:
        raise HTTPException(status_code=503, detail="DAG validator not available")

    validator = await get_dag_validator()
    validation = await validator.validate_dag(
        request.dag_id,
        request.params,
    )

    return {
        "dag_id": request.dag_id,
        "is_valid": validation.is_valid,
        "can_proceed": validation.can_proceed,
        "overall_status": validation.overall_status.value,
        "checks": [
            {
                "name": c.name,
                "status": c.status.value,
                "message": c.message,
                "fix_suggestion": c.fix_suggestion,
            }
            for c in validation.checks
        ],
        "user_actions": validation.user_actions,
        "error_summary": validation.error_summary,
        "timestamp": time.time(),
    }


@app.post("/orchestrator/dags/generate")
async def generate_dag(request: DAGCreateRequest):
    """
    Generate a new DAG based on task requirements.

    Returns the generated DAG code for user review.
    Requires approval before deployment.
    Per ADR-0066: DAG Validation and Creation.
    """
    if not DAG_VALIDATOR_AVAILABLE:
        raise HTTPException(status_code=503, detail="DAG validator not available")

    validator = await get_dag_validator()

    creation_request = DAGCreationRequest(
        dag_id=request.dag_id,
        description=request.description,
        task_description=request.task_description,
        source_project=request.source_project,
        params=request.params,
    )

    result = await validator.generate_dag(creation_request)

    return {
        "success": result.success,
        "dag_id": result.dag_id,
        "file_path": result.file_path,
        "preview": result.preview,
        "dag_code": result.dag_code,
        "requires_approval": result.requires_approval,
        "error": result.error,
        "user_actions": [
            {
                "action_type": "approve",
                "description": "Deploy this DAG to Airflow",
                "endpoint": "/orchestrator/dags/approve",
            },
            {
                "action_type": "modify",
                "description": "Request changes to the DAG",
                "endpoint": "/orchestrator/dags/generate",
            },
            {
                "action_type": "reject",
                "description": "Cancel DAG creation",
            },
        ],
        "timestamp": time.time(),
    }


@app.post("/orchestrator/dags/approve")
async def approve_dag(request: DAGApproveRequest):
    """
    Approve and deploy a generated DAG.

    Writes the DAG to the Airflow dags folder.
    Per ADR-0066: DAG Validation and Creation.
    """
    if not DAG_VALIDATOR_AVAILABLE:
        raise HTTPException(status_code=503, detail="DAG validator not available")

    validator = await get_dag_validator()

    success, message = await validator.deploy_dag(
        request.dag_code,
        request.file_path,
    )

    if not success:
        raise HTTPException(
            status_code=500,
            detail=message,
        )

    return {
        "success": True,
        "dag_id": request.dag_id,
        "file_path": request.file_path,
        "message": message,
        "next_steps": [
            f"DAG deployed to {request.file_path}",
            "Airflow will detect the new DAG within 30 seconds",
            f"Trigger with: airflow dags trigger {request.dag_id}",
        ],
        "timestamp": time.time(),
    }


@app.get("/orchestrator/dags/{dag_id}")
async def get_dag_info(dag_id: str):
    """
    Get detailed information about a specific DAG.

    Includes validation status and available parameters.
    """
    if not DAG_VALIDATOR_AVAILABLE:
        raise HTTPException(status_code=503, detail="DAG validator not available")

    validator = await get_dag_validator()
    await validator.discover_dags()

    dag_info = validator._dag_cache.get(dag_id)
    if not dag_info:
        raise HTTPException(status_code=404, detail=f"DAG not found: {dag_id}")

    return {
        "dag_id": dag_info.dag_id,
        "file_path": dag_info.file_path,
        "description": dag_info.description,
        "schedule": dag_info.schedule,
        "tags": dag_info.tags,
        "params": dag_info.params,
        "status": dag_info.status.value,
        "timestamp": time.time(),
    }


# =============================================================================
# Project File Editing Endpoints (ADR-0066 Phase 3)
# =============================================================================

# Import project editor
try:
    from project_editor import (
        get_project_editor,
        propose_file_edit,
        apply_approved_edit,
        EditType,  # noqa: F401
    )

    PROJECT_EDITOR_AVAILABLE = True
except ImportError:
    PROJECT_EDITOR_AVAILABLE = False
    logger.warning("Project editor not available")


class FileEditRequest(BaseModel):
    """Request for proposing a file edit."""

    project_path: str
    file_path: str
    content: str
    reason: str
    edit_type: str = "modify"  # create, modify, delete


class EditApproveRequest(BaseModel):
    """Request for approving an edit."""

    edit_id: str
    commit: bool = True


class EditRejectRequest(BaseModel):
    """Request for rejecting an edit."""

    edit_id: str
    reason: str = ""


@app.get("/orchestrator/projects/edits")
async def list_pending_edits():
    """
    List all pending file edits awaiting approval.

    Per ADR-0066: Project File Editing.
    """
    if not PROJECT_EDITOR_AVAILABLE:
        raise HTTPException(status_code=503, detail="Project editor not available")

    editor = get_project_editor()
    pending = editor.get_all_pending_edits()

    return {
        "pending_edits": [
            {
                "edit_id": e.edit_id,
                "project_path": e.project_path,
                "file_path": e.file_path,
                "edit_type": e.edit_type.value,
                "status": e.status.value,
                "reason": e.reason,
                "created_at": e.created_at.isoformat(),
            }
            for e in pending
        ],
        "total": len(pending),
        "timestamp": time.time(),
    }


@app.get("/orchestrator/projects/edits/{edit_id}")
async def get_edit_details(edit_id: str):
    """
    Get details of a specific edit including diff preview.

    Per ADR-0066: Project File Editing.
    """
    if not PROJECT_EDITOR_AVAILABLE:
        raise HTTPException(status_code=503, detail="Project editor not available")

    editor = get_project_editor()
    edit = editor.get_pending_edit(edit_id)

    if not edit:
        raise HTTPException(status_code=404, detail=f"Edit not found: {edit_id}")

    return {
        "edit_id": edit.edit_id,
        "project_path": edit.project_path,
        "file_path": edit.file_path,
        "edit_type": edit.edit_type.value,
        "status": edit.status.value,
        "reason": edit.reason,
        "diff": edit.diff,
        "created_at": edit.created_at.isoformat(),
        "current_content_preview": (edit.current_content or "")[:500],
        "proposed_content_preview": edit.proposed_content[:500],
        "user_actions": [
            {
                "action_type": "approve",
                "description": "Approve and apply this edit",
                "endpoint": f"/orchestrator/projects/edits/{edit_id}/approve",
            },
            {
                "action_type": "reject",
                "description": "Reject this edit",
                "endpoint": f"/orchestrator/projects/edits/{edit_id}/reject",
            },
        ],
        "timestamp": time.time(),
    }


@app.post("/orchestrator/projects/edits/propose")
async def propose_edit(request: FileEditRequest):
    """
    Propose an edit to a project file.

    The edit will be pending until approved or rejected.
    Per ADR-0066: Project File Editing.
    """
    if not PROJECT_EDITOR_AVAILABLE:
        raise HTTPException(status_code=503, detail="Project editor not available")

    result = propose_file_edit(
        project_path=request.project_path,
        file_path=request.file_path,
        content=request.content,
        reason=request.reason,
        edit_type=request.edit_type,
    )

    return {
        **result,
        "timestamp": time.time(),
    }


@app.post("/orchestrator/projects/edits/{edit_id}/approve")
async def approve_edit(edit_id: str, commit: bool = True):
    """
    Approve and apply a pending edit.

    Optionally creates a git commit for the change.
    Per ADR-0066: Project File Editing.
    """
    if not PROJECT_EDITOR_AVAILABLE:
        raise HTTPException(status_code=503, detail="Project editor not available")

    result = apply_approved_edit(edit_id, commit=commit)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])

    return {
        **result,
        "timestamp": time.time(),
    }


@app.post("/orchestrator/projects/edits/{edit_id}/reject")
async def reject_edit(edit_id: str, reason: str = ""):
    """
    Reject a pending edit.

    Per ADR-0066: Project File Editing.
    """
    if not PROJECT_EDITOR_AVAILABLE:
        raise HTTPException(status_code=503, detail="Project editor not available")

    editor = get_project_editor()
    success, message = editor.reject_edit(edit_id, reason)

    if not success:
        raise HTTPException(status_code=400, detail=message)

    return {
        "success": True,
        "edit_id": edit_id,
        "message": message,
        "timestamp": time.time(),
    }


@app.post("/orchestrator/projects/edits/{edit_id}/rollback")
async def rollback_edit(edit_id: str):
    """
    Rollback an applied edit using the backup.

    Per ADR-0066: Project File Editing.
    """
    if not PROJECT_EDITOR_AVAILABLE:
        raise HTTPException(status_code=503, detail="Project editor not available")

    editor = get_project_editor()
    result = editor.rollback_edit(edit_id)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)

    return {
        "success": True,
        "edit_id": result.edit_id,
        "message": result.message,
        "timestamp": time.time(),
    }


# =============================================================================
# Smart Pipeline Execution Endpoints (ADR-0066 Phase 4)
# =============================================================================

# Import smart pipeline
try:
    from smart_pipeline import (
        get_smart_orchestrator,
        execute_smart_pipeline,
    )

    SMART_PIPELINE_AVAILABLE = True
except ImportError:
    SMART_PIPELINE_AVAILABLE = False
    logger.warning("Smart pipeline not available")


class ExecuteRequest(BaseModel):
    """Request for smart pipeline execution."""

    dag_id: str
    params: dict = {}
    validate_first: bool = True
    smart_pipeline: bool = True


class EscalateRequest(BaseModel):
    """Request for escalating an execution."""

    execution_id: str
    reason: str


@app.post("/orchestrator/execute")
async def execute_pipeline(request: ExecuteRequest):
    """
    Execute a DAG with smart pipeline features.

    Features:
    - Pre-execution validation
    - OpenLineage tracking
    - Execution monitoring
    - User action recommendations

    Per ADR-0066: Smart Pipeline Deployment.
    """
    if not SMART_PIPELINE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Smart pipeline not available")

    result = await execute_smart_pipeline(
        dag_id=request.dag_id,
        params=request.params,
        validate_first=request.validate_first,
    )

    return {
        **result,
        "timestamp": time.time(),
    }


@app.get("/orchestrator/executions/{execution_id}/status")
async def get_execution_status(execution_id: str):
    """
    Get the status of a pipeline execution.

    Includes current status, monitoring info, and user actions.
    Per ADR-0066: Smart Pipeline Deployment.
    """
    if not SMART_PIPELINE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Smart pipeline not available")

    orchestrator = await get_smart_orchestrator()
    execution = await orchestrator.get_execution_status(execution_id)

    if not execution:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")

    return {
        "execution_id": execution.execution_id,
        "dag_id": execution.dag_id,
        "run_id": execution.run_id,
        "status": execution.status.value,
        "triggered_at": execution.triggered_at.isoformat() if execution.triggered_at else None,
        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
        "validation_passed": execution.validation_passed,
        "failed_task": execution.failed_task,
        "error_message": execution.error_message,
        "monitoring": {
            "airflow_ui_url": execution.monitoring.airflow_ui_url,
            "status_endpoint": execution.monitoring.status_endpoint,
            "expected_duration_minutes": execution.monitoring.expected_duration_minutes,
        }
        if execution.monitoring
        else None,
        "user_actions": [
            {
                "action_type": a.action_type.value,
                "description": a.description,
                "command": a.command,
                "api_endpoint": a.api_endpoint,
                "difficulty": a.difficulty,
            }
            for a in execution.user_actions
        ],
        "escalation_needed": execution.escalation_needed,
        "escalation_reason": execution.escalation_reason,
        "timestamp": time.time(),
    }


@app.post("/orchestrator/executions/{execution_id}/cancel")
async def cancel_execution(execution_id: str):
    """
    Cancel a running execution.

    Per ADR-0066: Smart Pipeline Deployment.
    """
    if not SMART_PIPELINE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Smart pipeline not available")

    orchestrator = await get_smart_orchestrator()
    result = await orchestrator.cancel_execution(execution_id)

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to cancel"))

    return {
        **result,
        "timestamp": time.time(),
    }


@app.post("/orchestrator/escalate")
async def escalate_execution(request: EscalateRequest):
    """
    Escalate an execution to Manager Agent.

    Provides context for the Manager to assist.
    Per ADR-0066: Smart Pipeline Deployment.
    """
    if not SMART_PIPELINE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Smart pipeline not available")

    orchestrator = await get_smart_orchestrator()
    result = await orchestrator.escalate_execution(
        request.execution_id,
        request.reason,
    )

    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to escalate"))

    return {
        **result,
        "message": "Escalation registered. Manager Agent will review.",
        "timestamp": time.time(),
    }


@app.get("/orchestrator/executions/{execution_id}/validate")
async def validate_execution_outcome(
    execution_id: str,
    emit_to_openlineage: bool = True,
    retry_count: int = 0,
):
    """
    Validate the outcome of an execution - detect shadow errors.

    This endpoint:
    1. Checks if the expected outcome was achieved (e.g., VM created)
    2. Analyzes task logs for shadow errors (failures that didn't fail the task)
    3. Provides actionable fix suggestions with ModelRetry pattern
    4. Emits DataQuality facets to Marquez/OpenLineage for Manager Agent

    Per ADR-0066: Shadow Error Detection.
    Enhanced with PydanticAI ModelRetry pattern and OpenLineage integration.
    """
    if not SMART_PIPELINE_AVAILABLE:
        raise HTTPException(status_code=503, detail="Smart pipeline not available")

    orchestrator = await get_smart_orchestrator()
    execution = await orchestrator.get_execution_status(execution_id)

    if not execution:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")

    # Run outcome validation with OpenLineage emission
    validation_result = await orchestrator.validate_outcome(
        execution,
        emit_to_openlineage=emit_to_openlineage,
        retry_count=retry_count,
    )

    # Determine overall status
    airflow_says_success = execution.status.value == "success"
    outcome_validated = validation_result.get("validated", False)
    has_shadow_errors = len(validation_result.get("shadow_errors", [])) > 0

    # Detect discrepancy
    is_shadow_failure = airflow_says_success and (not outcome_validated or has_shadow_errors)

    return {
        "execution_id": execution_id,
        "dag_id": execution.dag_id,
        "airflow_status": execution.status.value,
        "outcome_validation": {
            "validated": outcome_validated,
            "expected": validation_result.get("expected_outcome"),
            "actual": validation_result.get("actual_outcome"),
        },
        "shadow_errors": validation_result.get("shadow_errors", []),
        "is_shadow_failure": is_shadow_failure,
        "fix_suggestions": [
            {
                "action_type": a.action_type.value,
                "description": a.description,
                "command": a.command,
                "difficulty": a.difficulty,
            }
            for a in validation_result.get("fix_suggestions", [])
        ],
        # ModelRetry pattern fields
        "model_retry": validation_result.get("model_retry"),
        "can_self_correct": validation_result.get("can_self_correct", False),
        "corrected_params": validation_result.get("corrected_params", {}),
        # OpenLineage tracking
        "openlineage_emitted": validation_result.get("openlineage_emitted", False),
        "summary": (
            "SHADOW FAILURE DETECTED: Airflow reported success but outcome validation failed. Review shadow_errors and fix_suggestions."
            if is_shadow_failure
            else "Execution validated successfully"
            if outcome_validated
            else "Execution completed - outcome validation not applicable"
        ),
        "timestamp": time.time(),
    }


# Import query function for Manager Agent
try:
    from smart_pipeline import query_shadow_errors_for_manager

    SHADOW_ERROR_QUERY_AVAILABLE = True
except ImportError:
    SHADOW_ERROR_QUERY_AVAILABLE = False


@app.get("/orchestrator/shadow-errors")
async def get_shadow_errors_for_manager(
    dag_id: Optional[str] = None,
    since_hours: int = 24,
):
    """
    Query shadow errors from Marquez/OpenLineage for the Manager Agent.

    This endpoint enables the Manager Agent to:
    - Understand patterns in shadow failures across DAGs
    - Make decisions about escalation and remediation
    - Track recurring issues over time

    The response includes aggregated error types, recommendations,
    and recent shadow error events from the OpenLineage tracking.

    Per ADR-0066: Manager Agent Integration.
    """
    if not SHADOW_ERROR_QUERY_AVAILABLE:
        raise HTTPException(status_code=503, detail="Shadow error query not available")

    result = await query_shadow_errors_for_manager(
        dag_id=dag_id,
        since_hours=since_hours,
    )

    return {
        **result,
        "endpoint": "/orchestrator/shadow-errors",
        "description": "Shadow error summary for Manager Agent decision-making",
        "timestamp": time.time(),
    }


# =============================================================================
# Full Feedback Loop Endpoints (ADR-0066 Phase 5)
# =============================================================================

# Import feedback loop
try:
    from feedback_loop import (
        get_feedback_orchestrator,
        execute_user_intent,
    )

    FEEDBACK_LOOP_AVAILABLE = True
except ImportError:
    FEEDBACK_LOOP_AVAILABLE = False
    logger.warning("Feedback loop not available")


class IntentRequest(BaseModel):
    """Request for executing user intent through the full flow."""

    intent: str
    params: dict = {}
    auto_approve: bool = False
    auto_execute: bool = True


@app.post("/orchestrator/intent")
async def process_user_intent(request: IntentRequest):
    """
    Process a user intent through the complete orchestration flow.

    This is the main entry point for ADR-0066 functionality.
    It integrates:
    - Phase 1: Project Discovery
    - Phase 2: DAG Validation/Creation
    - Phase 3: Project Editing
    - Phase 4: Smart Pipeline Execution
    - Phase 5: Feedback Loop

    Example:
        POST /orchestrator/intent
        {"intent": "Create a CentOS 9 VM with 8GB RAM", "params": {"vm_profile": "centos9stream"}}

    Returns:
        Complete flow result with status, execution info, and user actions.
    """
    if not FEEDBACK_LOOP_AVAILABLE:
        raise HTTPException(status_code=503, detail="Feedback loop not available")

    result = await execute_user_intent(
        user_intent=request.intent,
        params=request.params,
        auto_approve=request.auto_approve,
        auto_execute=request.auto_execute,
    )

    return {
        **result,
        "timestamp": time.time(),
    }


@app.get("/orchestrator/flows/{flow_id}")
async def get_flow_status(flow_id: str):
    """
    Get the status of an orchestration flow.

    Per ADR-0066: Full Feedback Loop.
    """
    if not FEEDBACK_LOOP_AVAILABLE:
        raise HTTPException(status_code=503, detail="Feedback loop not available")

    orchestrator = await get_feedback_orchestrator()
    context = orchestrator.get_flow_status(flow_id)

    if not context:
        raise HTTPException(status_code=404, detail=f"Flow not found: {flow_id}")

    return {
        "flow_id": context.flow_id,
        "user_intent": context.user_intent,
        "current_step": context.current_step.value,
        "status": context.status.value,
        "source_project": context.source_project,
        "dag_id": context.dag_id,
        "dag_found": context.dag_found,
        "dag_created": context.dag_created,
        "execution_id": context.execution_id,
        "execution_status": context.execution_status,
        "user_actions": context.user_actions,
        "error_message": context.error_message,
        "timestamp": time.time(),
    }


# =============================================================================
# Lineage Observer Endpoints (ADR-0066 - Comprehensive DAG Monitoring)
# =============================================================================

# Import Observer
try:
    from agents.observer import observe_dag_run  # noqa: F401

    OBSERVER_AVAILABLE = True
except ImportError:
    OBSERVER_AVAILABLE = False
    logger.warning("Observer module not available")


@app.get("/orchestrator/observe/{dag_id}/{run_id}")
async def observe_dag_execution(
    dag_id: str,
    run_id: str,
    check_logs: bool = True,
):
    """
    Observe a DAG run with comprehensive feedback.

    The Observer Agent ALWAYS reports back with full status,
    regardless of pass/fail. This includes:
    - Overall status (running/success/failed)
    - Task-level progress
    - Shadow error detection (errors in logs even when task succeeds)
    - Concerns and recommendations

    This endpoint addresses the "shadow error" problem where DAG
    failures weren't being detected in CI/CD pipelines.

    Args:
        dag_id: The DAG to observe
        run_id: The specific run ID to observe
        check_logs: Whether to fetch and analyze task logs (default: true)

    Returns:
        Complete observation report with concerns and recommendations
    """
    if not OBSERVER_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Observer module not available",
        )

    report = await observe_dag_run(dag_id, run_id, check_logs)

    return {
        **report,
        "endpoint": f"/orchestrator/observe/{dag_id}/{run_id}",
        "timestamp": time.time(),
    }


@app.post("/orchestrator/observe")
async def observe_dag_by_name(
    dag_id: str,
    check_logs: bool = True,
):
    """
    Observe the latest run of a DAG.

    Automatically finds the most recent run and observes it.
    """
    if not OBSERVER_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Observer module not available",
        )

    # Get the latest run ID from Airflow
    try:
        import httpx

        airflow_url = os.getenv("AIRFLOW_API_URL", "http://localhost:8888")
        airflow_user = os.getenv("AIRFLOW_API_USER", "admin")
        airflow_pass = os.getenv("AIRFLOW_API_PASSWORD", "admin")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{airflow_url}/api/v1/dags/{dag_id}/dagRuns",
                params={"limit": 1, "order_by": "-execution_date"},
                auth=(airflow_user, airflow_pass),
            )
            if response.status_code != 200:
                raise HTTPException(
                    status_code=404,
                    detail=f"Could not find runs for DAG: {dag_id}",
                )

            data = response.json()
            runs = data.get("dag_runs", [])
            if not runs:
                # No runs yet - return a "pending" status instead of 404
                # This helps CI workflows that call observe right after triggering
                return {
                    "dag_id": dag_id,
                    "run_id": None,
                    "overall_status": "pending",
                    "is_complete": False,
                    "success": False,
                    "progress_percent": 0.0,
                    "total_tasks": 0,
                    "completed_tasks": 0,
                    "failed_tasks": 0,
                    "running_tasks": 0,
                    "task_statuses": {},
                    "failed_task_details": [],
                    "concerns": [],
                    "has_warnings": False,
                    "has_errors": False,
                    "recommendations": [f"DAG '{dag_id}' has no runs yet - waiting for first run to start"],
                    "summary": f"DAG '{dag_id}' is waiting to start (no runs yet)",
                    "detailed_message": f"DAG '{dag_id}' has been triggered but no run has started yet. This is normal - the scheduler may take a few seconds to pick up the DAG.",
                    "endpoint": "/orchestrator/observe",
                    "timestamp": time.time(),
                }

            run_id = runs[0].get("dag_run_id")

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Could not connect to Airflow: {e}",
        )

    report = await observe_dag_run(dag_id, run_id, check_logs)

    return {
        **report,
        "endpoint": "/orchestrator/observe",
        "timestamp": time.time(),
    }


# =============================================================================
# RAG Pre-flight Endpoint
# =============================================================================


@app.get("/orchestrator/rag/preflight")
async def rag_preflight_endpoint(force: bool = False):
    """
    Run RAG pre-flight checks and return results.

    Detects empty RAG state (0 documents loaded) and auto-fixes
    by triggering /orchestrator/context/reload. Useful for operators
    to verify RAG health after container restarts.

    Args:
        force: Bypass cache and re-run all checks (default: False)
    """
    try:
        from intent_parser.rag_preflight import run_rag_preflight
        result = await run_rag_preflight(force=force)
        return {
            "checks": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "message": c.message,
                    "fix_applied": c.fix_applied,
                }
                for c in result.checks
            ],
            "can_proceed": result.can_proceed,
            "summary": result.summary,
            "label": result.label,
            "timestamp": time.time(),
        }
    except ImportError:
        raise HTTPException(status_code=503, detail="RAG preflight module not available")
    except Exception as e:
        logger.error(f"RAG preflight endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"RAG preflight error: {str(e)}")


def main():
    """Main entry point."""
    # Get configuration from environment
    host = os.getenv("AI_HOST", "0.0.0.0")
    port = int(os.getenv("AI_PORT", "8080"))
    log_level = os.getenv("AI_LOG_LEVEL", "info")

    # Start the server
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        log_level=log_level,
        reload=False,  # Disable reload in production
    )


if __name__ == "__main__":
    main()
