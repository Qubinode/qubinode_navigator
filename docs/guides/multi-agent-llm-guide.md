---
title: Multi-Agent LLM Guide
parent: Guides
nav_order: 2
---

# Multi-Agent LLM System Guide

**ADR-0049: Multi-Agent LLM Memory Architecture**

This guide explains how to use the Qubinode multi-agent LLM system for intelligent DAG development and troubleshooting.

## Overview

The multi-agent system provides:

- **Persistent Memory**: RAG-based knowledge base that persists across sessions
- **Intelligent Assistance**: Context-aware help using project documentation
- **Troubleshooting History**: Learn from past solutions
- **Code Lineage**: Track what code produced what results

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Calling LLM (Claude/GPT-4)                  │
│                    User Interface & Override Authority          │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        MCP Server                                │
│    Tools: RAG, Troubleshooting, Lineage, DAG Management         │
└─────────────────────────────┬───────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │  RAG Store   │  │   Lineage    │  │   Agents     │
    │  (PgVector)  │  │  (Marquez)   │  │   (LiteLLM)  │
    └──────────────┘  └──────────────┘  └──────────────┘
```

## Getting Started

### 1. Start the System

```bash
cd airflow

# Start core services
docker-compose up -d

# Enable MCP server (optional)
export AIRFLOW_MCP_ENABLED=true
docker-compose --profile mcp up -d

# Enable lineage tracking (optional)
docker-compose --profile lineage up -d
```

### 2. Bootstrap RAG Knowledge Base

```bash
# Trigger the bootstrap DAG
airflow dags trigger rag_bootstrap

# Or via Airflow UI
# Navigate to DAGs > rag_bootstrap > Trigger
```

### 3. Connect Your LLM

Configure your LLM (Claude Code, Cursor, etc.) to use the MCP server:

```json
{
  "mcpServers": {
    "qubinode-airflow": {
      "command": "curl",
      "args": ["-N", "http://localhost:8889/sse"]
    }
  }
}
```

## MCP Tools Reference

### RAG Tools

| Tool                                       | Description                    |
| ------------------------------------------ | ------------------------------ |
| `query_rag(query, doc_types, limit)`       | Search knowledge base          |
| `ingest_to_rag(content, doc_type, source)` | Add new documents              |
| `get_rag_stats()`                          | View knowledge base statistics |

**Example:**

```
query_rag("How do I create a FreeIPA deployment DAG?")
```

### Troubleshooting Tools

| Tool                                                  | Description         |
| ----------------------------------------------------- | ------------------- |
| `get_troubleshooting_history(error_pattern)`          | Find past solutions |
| `log_troubleshooting_attempt(task, solution, result)` | Record attempts     |

**Example:**

```
get_troubleshooting_history(error_pattern="SSH connection refused")
```

### Lineage Tools

| Tool                                        | Description                |
| ------------------------------------------- | -------------------------- |
| `get_dag_lineage(dag_id)`                   | View DAG dependencies      |
| `get_failure_blast_radius(dag_id, task_id)` | Analyze failure impact     |
| `get_dataset_lineage(dataset_name)`         | Track data flow            |
| `get_lineage_stats()`                       | View lineage system status |

**Example:**

```
get_failure_blast_radius("freeipa_deployment", "install_freeipa")
```

### DAG Management Tools

| Tool                   | Description       |
| ---------------------- | ----------------- |
| `list_dags()`          | List all DAGs     |
| `get_dag_info(dag_id)` | Get DAG details   |
| `trigger_dag(dag_id)`  | Trigger a DAG run |

## Four Core Policies

The system follows four policies that guide decision-making:

### Policy 1: Confidence & RAG Enrichment

> "Don't guess - use RAG for context"

- All decisions are informed by RAG queries
- Low confidence triggers escalation to you
- You'll see confidence scores in responses

### Policy 2: Provider-First Rule

> "Always use official Airflow providers"

- System checks for providers before custom code
- Uses `check_provider_exists()` automatically
- Suggests appropriate operators

### Policy 3: Missing Provider → Plan, Not Code

> "No provider? Generate a plan first"

- When no provider exists, generates implementation plan
- Requests approval before writing code
- Documents risks and alternatives

### Policy 4: Override Authority

> "You have final say"

- You can override any system decision
- Use explicit instructions to bypass policies
- Overrides are logged for learning

## Workflow Examples

### Creating a New DAG

1. **Ask the LLM:**

   ```
   Create a DAG to deploy a FreeIPA server using kcli
   ```

1. **System Response:**

   - Queries RAG for similar DAGs
   - Checks for relevant providers
   - Computes confidence score
   - Either generates code or requests more info

1. **If confidence is low:**

   ```
   The system needs more information:
   - What SSH connection should be used?
   - What FreeIPA version?

   You can provide details or override with:
   "Use ssh_conn_id='freeipa_host' and version 4.11"
   ```

### Troubleshooting a Failure

1. **Describe the error:**

   ```
   My freeipa_deployment DAG is failing with "DNS resolution failed"
   ```

1. **System Response:**

   - Searches troubleshooting history
   - Finds similar past issues
   - Analyzes blast radius
   - Suggests solutions based on what worked before

1. **After you fix it:**

   ```
   log_troubleshooting_attempt(
     task="freeipa_deployment.install_freeipa",
     solution="Added DNS entry to /etc/hosts",
     result="success"
   )
   ```

### Understanding Lineage

1. **Query lineage:**

   ```
   get_dag_lineage("freeipa_deployment")
   ```

1. **Before retrying a failed task:**

   ```
   get_failure_blast_radius("freeipa_deployment", "configure_dns")
   ```

## Configuration

### Environment Variables

| Variable               | Default                                | Description                       |
| ---------------------- | -------------------------------------- | --------------------------------- |
| `AIRFLOW_MCP_ENABLED`  | false                                  | Enable MCP server                 |
| `AIRFLOW_MCP_PORT`     | 8889                                   | MCP server port                   |
| `OPENLINEAGE_DISABLED` | true                                   | Disable lineage tracking          |
| `EMBEDDING_PROVIDER`   | local                                  | Embedding provider (local/openai) |
| `EMBEDDING_MODEL`      | sentence-transformers/all-MiniLM-L6-v2 | Model for embeddings              |

### Confidence Thresholds

| Level      | Threshold | Action               |
| ---------- | --------- | -------------------- |
| High       | >= 0.8    | Auto-execute         |
| Medium     | 0.6 - 0.8 | Execute with logging |
| Low-Medium | 0.4 - 0.6 | Request approval     |
| Low        | \< 0.4    | Escalate to user     |

## Troubleshooting

### RAG queries return no results

1. Run the bootstrap DAG:

   ```bash
   airflow dags trigger rag_bootstrap
   ```

1. Check document count:

   ```
   get_rag_stats()
   ```

1. Lower the similarity threshold:

   ```
   query_rag("your query", threshold=0.3)
   ```

### Lineage not tracking

1. Enable lineage profile:

   ```bash
   docker-compose --profile lineage up -d
   ```

1. Set environment variable:

   ```bash
   export OPENLINEAGE_DISABLED=false
   ```

1. Verify Marquez is running:

   ```bash
   curl http://localhost:5001/api/v1/namespaces
   ```

### MCP server not responding

1. Check if enabled:

   ```bash
   export AIRFLOW_MCP_ENABLED=true
   ```

1. Restart the MCP service:

   ```bash
   docker-compose --profile mcp restart airflow-mcp-server
   ```

1. Check logs:

   ```bash
   docker-compose logs airflow-mcp-server
   ```

## Best Practices

1. **Bootstrap after deployment**: Always run `rag_bootstrap` after initial setup
1. **Log troubleshooting**: Record what worked to help future sessions
1. **Use lineage for impact analysis**: Check blast radius before retrying failures
1. **Provide context**: The more context you give, the better the assistance
1. **Override when confident**: If you know the answer, use override to skip checks

## Related Documentation

- [ADR-0049: Multi-Agent LLM Memory Architecture](../adrs/adr-0049-multi-agent-llm-memory-architecture.md)
- [ADR-0049 Implementation Plan](../adrs/adr-0049-implementation-plan.md)
- [ADR-0046: DAG Factory Pattern](../adrs/adr-0046-dag-validation-pipeline-and-host-execution.md)
