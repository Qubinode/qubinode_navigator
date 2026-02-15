# ADR-0063: PydanticAI Core Agent Orchestrator

## Status

**ACCEPTED** - Implemented (2025-12-05)

## Context

### The Problem

The original AI Assistant architecture (ADR-0027) faced several limitations:

1. **Single-Model Constraints**: Local Granite models (8B parameters) lack the capacity for complex architectural decisions and planning
1. **No Multi-Step Orchestration**: Tasks requiring multiple phases (planning → validation → execution → monitoring) were difficult to coordinate
1. **Limited Provider Support**: Tied to llama.cpp and local models, preventing use of cloud LLMs with better reasoning capabilities
1. **No Type-Safe Responses**: Free-form text responses made it difficult to validate and process agent outputs programmatically

### Why PydanticAI?

After evaluating multiple agent frameworks (LangChain, LlamaIndex, AutoGen), PydanticAI emerged as the best fit:

| Framework      | Pros                                                                  | Cons                                     | Decision                  |
| -------------- | --------------------------------------------------------------------- | ---------------------------------------- | ------------------------- |
| **PydanticAI** | Type-safe, multi-provider, minimal dependencies, excellent validation | New framework, smaller community         | ✅ **SELECTED**           |
| LangChain      | Mature, extensive ecosystem                                           | Heavy dependencies, complex abstractions | ❌ Too complex            |
| LlamaIndex     | Excellent RAG support                                                 | Focused on retrieval, not orchestration  | ❌ Limited orchestration  |
| AutoGen        | Multi-agent conversations                                             | Complex setup, resource-intensive        | ❌ Overkill for our needs |

**Key PydanticAI Advantages:**

- **Type-Safe Agent Responses**: Uses Pydantic models for structured, validated outputs
- **Multi-Provider Support**: Single API for Google, OpenAI, Anthropic, OpenRouter, Ollama, Groq
- **Tool Integration**: Native support for function calling and MCP (Model Context Protocol)
- **Validation Layer**: Automatic validation of agent outputs with retry logic
- **Minimal Dependencies**: Lightweight compared to LangChain/LlamaIndex

## Decision

### 1. Multi-Agent Architecture with PydanticAI

Implement a three-agent system using PydanticAI:

```
┌─────────────────────────────────────────────────────────────────┐
│                      User Intent / Request                       │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │      Manager Agent           │
              │  (Session Orchestration)     │
              │  - Creates execution plans   │
              │  - Identifies dependencies   │
              │  - Routes to Developer       │
              └──────────────┬───────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │     Developer Agent          │
              │  (Task Orchestration)        │
              │  - Validates prerequisites   │
              │  - Queries RAG/Lineage       │
              │  - Delegates to Aider        │
              └──────────────┬───────────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │      Observer Agent          │
              │  (Execution Monitoring)      │
              │  - Tracks DAG status         │
              │  - Detects shadow errors     │
              │  - Provides feedback         │
              └──────────────────────────────┘
```

### 2. Agent Responsibilities

#### Manager Agent

- **Role**: Session orchestration and planning
- **Model**: `MANAGER_MODEL` (default: google-gla:gemini-2.0-flash)
- **Output**: `SessionPlan` (Pydantic model)
- **Responsibilities**:
  - Analyze user intent and create execution plan
  - Identify required Airflow providers
  - Set escalation triggers for complex operations
  - Delegate tasks to Developer Agent

#### Developer Agent

- **Role**: Task orchestration (NOT code generation)
- **Model**: `DEVELOPER_MODEL` (default: google-gla:gemini-2.0-flash)
- **Output**: `DeveloperTaskResult` (Pydantic model)
- **Responsibilities**:
  - Validate DAG prerequisites
  - Query RAG for documentation
  - Check Marquez for execution history
  - Compute confidence scores
  - Delegate code generation to Aider or return `FallbackCodePrompt`

**IMPORTANT**: The Developer Agent does NOT write code directly. It orchestrates:

- **Option 1**: Aider + LiteLLM (when API keys available)
- **Option 2**: Return `FallbackCodePrompt` to calling LLM

#### Observer Agent

- **Role**: DAG execution monitoring and feedback
- **Model**: `PYDANTICAI_MODEL` (default: google-gla:gemini-2.0-flash)
- **Output**: `ObserverReport` (Pydantic model)
- **Responsibilities**:
  - Monitor DAG run status via Airflow API
  - Detect shadow errors (errors that don't fail the DAG)
  - Query OpenLineage for execution lineage
  - Provide actionable feedback

### 3. Type-Safe Agent Communication

All agents use Pydantic models for structured I/O:

```python
# Manager Agent Output
class SessionPlan(BaseModel):
    """Execution plan created by Manager Agent."""
    dag_id: str
    execution_steps: List[str]
    required_providers: List[str]
    escalation_triggers: List[str]
    estimated_duration_minutes: int

# Developer Agent Output
class DeveloperTaskResult(BaseModel):
    """Task result from Developer Agent."""
    task_status: str  # "ready", "needs_code_gen", "blocked"
    confidence: float  # 0.0 to 1.0
    code_generation_mode: str  # "none", "aider", "fallback_prompt"
    prerequisites_met: bool
    validation_errors: List[str]

# Observer Agent Output
class ObserverReport(BaseModel):
    """Monitoring report from Observer Agent."""
    execution_status: ExecutionStatus
    shadow_errors: List[ShadowError]
    concern_level: ConcernLevel
    recommendations: List[str]
```

### 4. Model Configuration

PydanticAI uses `provider:model` format (note the **colon**, not slash):

```bash
# Environment Variables
MANAGER_MODEL=google-gla:gemini-2.0-flash
DEVELOPER_MODEL=google-gla:gemini-2.0-flash
PYDANTICAI_MODEL=google-gla:gemini-2.0-flash

# Supported Providers
# Google Gemini
google-gla:gemini-2.0-flash
google-gla:gemini-1.5-pro

# OpenRouter (100+ models via single API)
openrouter:anthropic/claude-3.5-sonnet
openrouter:google/gemini-2.0-flash-exp
openrouter:openai/gpt-4o

# OpenAI
openai:gpt-4o
openai:gpt-4o-mini

# Anthropic
anthropic:claude-3-5-sonnet-latest
anthropic:claude-3-haiku-20240307

# Ollama (local models)
ollama:granite3.3:8b
ollama:llama3.3:70b

# Groq (fast inference)
groq:llama-3.3-70b-versatile
groq:mixtral-8x7b-32768
```

### 5. Integration with Existing Services

PydanticAI agents integrate with:

- **RAG Service**: Query documentation via MCP `query_rag` tool
- **Marquez/OpenLineage**: Get execution history via `get_dag_lineage` tool
- **Airflow API**: Trigger DAGs and monitor status
- **Aider (Optional)**: Code generation with LiteLLM models
- **PostgreSQL + PgVector**: Persistent memory and vector search (ADR-0049)

### 6. Intent-Based Deployment API

The orchestrator exposes FastAPI endpoints for natural language deployment:

```bash
# POST /orchestrator/intent
curl -X POST http://localhost:8080/orchestrator/intent \
  -H "Content-Type: application/json" \
  -d '{
    "intent": "Deploy FreeIPA server for identity management",
    "params": {"vm_name": "freeipa", "action": "create"},
    "auto_approve": true,
    "auto_execute": true
  }'

# Response: SessionPlan from Manager Agent
{
  "dag_id": "freeipa_deployment",
  "execution_steps": [...],
  "required_providers": ["ssh", "kcli"],
  "confidence": 0.95
}
```

## Consequences

### Positive

1. **Multi-Model Flexibility**: Can use best model for each task (fast models for orchestration, capable models for complex reasoning)
1. **Type Safety**: Pydantic validation ensures structured, predictable agent responses
1. **Provider Agnostic**: Easy to switch between Google, OpenAI, Anthropic, local models
1. **Separation of Concerns**: Clear boundaries between planning, orchestration, and execution
1. **Observable**: All agent interactions logged and traceable
1. **Cost Optimization**: Use cheap/fast models (Gemini Flash) for most tasks, reserve expensive models (GPT-4o, Claude Sonnet) for complex decisions

### Negative

1. **Cloud Dependency**: Requires API keys for full functionality (mitigated by Ollama fallback)
1. **New Framework**: PydanticAI is newer, less community resources than LangChain
1. **Model Costs**: Cloud LLM usage incurs costs (though much lower than GPT-4 for all tasks)
1. **Complexity**: Three-agent system is more complex than single-agent approach

### Risks & Mitigations

| Risk                        | Mitigation                                         |
| --------------------------- | -------------------------------------------------- |
| API outages                 | Fallback to Ollama local models                    |
| Cost overruns               | Default to Gemini Flash (cheapest/fastest)         |
| Agent coordination failures | Comprehensive error handling and retry logic       |
| Type validation errors      | PydanticAI's built-in validation and retry pattern |

## Implementation Status

- ✅ Manager Agent implemented with SessionPlan output
- ✅ Developer Agent implemented with DeveloperTaskResult output
- ✅ Observer Agent implemented with ObserverReport output
- ✅ Type-safe Pydantic models for all agent I/O
- ✅ Multi-provider support (Google, OpenAI, Anthropic, OpenRouter, Ollama, Groq)
- ✅ Intent-based deployment API (`/orchestrator/intent`)
- ✅ Integration with RAG service (PgVector + PostgreSQL per ADR-0049)
- ✅ Integration with Marquez/OpenLineage for execution history
- ✅ Aider integration for code generation (optional, with fallback)
- ✅ Comprehensive error handling and validation

## Related ADRs

- **[ADR-0027](adr-0027-cpu-based-ai-deployment-assistant-architecture.md)**: Original AI Assistant architecture (partially superseded)
- **[ADR-0049](adr-0049-multi-agent-llm-memory-architecture.md)**: Multi-Agent LLM Memory Architecture with PgVector
- **[ADR-0050](adr-0050-hybrid-host-container-architecture.md)**: Hybrid Host-Container Architecture
- **[ADR-0066](adr-0066-developer-agent-dag-validation-smart-pipelines.md)**: Developer Agent DAG Validation and Smart Pipelines

## References

- PydanticAI Documentation: https://ai.pydantic.dev/
- PydanticAI GitHub: https://github.com/pydantic/pydantic-ai
- Model Context Protocol (MCP): https://modelcontextprotocol.io/
- Aider + LiteLLM: https://aider.chat/docs/llms.html

______________________________________________________________________

*Status: Implemented*
*Last Updated: 2025-12-05*
*Implementation: `ai-assistant/src/agents/`*
