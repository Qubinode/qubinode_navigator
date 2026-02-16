---
nav_exclude: true
---

# MCP Developer Integration Guide

**For LLM Developers and Tool Builders**

This guide explains how to connect your LLM application to Qubinode Navigator's MCP servers for infrastructure automation.

______________________________________________________________________

## Table of Contents

1. [Overview](#overview)
1. [Available MCP Servers](#available-mcp-servers)
1. [Client Configuration](#client-configuration)
   - [Claude Desktop](#claude-desktop)
   - [Claude Code (CLI)](#claude-code-cli)
   - [Cursor IDE](#cursor-ide)
   - [Continue.dev](#continuedev)
   - [Custom Python Client](#custom-python-client)
   - [Custom Node.js Client](#custom-nodejs-client)
1. [Tool Reference](#tool-reference)
1. [LLM Interaction Patterns](#llm-interaction-patterns)
1. [Authentication](#authentication)
1. [Troubleshooting](#troubleshooting)

______________________________________________________________________

## Overview

Qubinode Navigator exposes two MCP (Model Context Protocol) servers that enable LLMs to manage infrastructure:

| Server               | Port | Purpose                                            | Tools |
| -------------------- | ---- | -------------------------------------------------- | ----- |
| **Airflow MCP**      | 8889 | Workflow orchestration, VM management, RAG queries | 25    |
| **AI Assistant MCP** | 8081 | Documentation search, AI chat                      | 4     |

**Protocol**: SSE (Server-Sent Events) over HTTP
**Authentication**: API Key via `X-API-Key` header
**Transport**: `mcp-remote` npm package or direct SSE client

______________________________________________________________________

## Available MCP Servers

### Airflow MCP Server (Port 8889)

The primary server for infrastructure operations:

```
Endpoint: http://<YOUR_SERVER>:8889/sse
Health:   http://<YOUR_SERVER>:8889/health
```

**Capabilities:**

- DAG management (list, trigger, status)
- VM lifecycle (create, delete, start, stop)
- RAG knowledge base queries
- Troubleshooting history
- Data lineage (OpenLineage/Marquez)

### AI Assistant MCP Server (Port 8081)

Secondary server for documentation and chat:

```
Endpoint: http://<YOUR_SERVER>:8081/sse
Health:   http://<YOUR_SERVER>:8081/health
```

**Capabilities:**

- RAG document search
- Context-aware AI chat
- Project status

______________________________________________________________________

## Client Configuration

### Claude Desktop

**Location:** `~/.config/claude/claude_desktop_config.json` (Linux/Mac) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows)

```json
{
  "mcpServers": {
    "qubinode-airflow": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://YOUR_SERVER_IP:8889/sse",
        "--header",
        "X-API-Key:${MCP_API_KEY}"
      ],
      "env": {
        "MCP_API_KEY": "YOUR_AIRFLOW_API_KEY"
      }
    },
    "qubinode-ai": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://YOUR_SERVER_IP:8081/sse",
        "--header",
        "X-API-Key:${MCP_API_KEY}"
      ],
      "env": {
        "MCP_API_KEY": "YOUR_AI_ASSISTANT_API_KEY"
      }
    }
  }
}
```

**After saving:** Restart Claude Desktop completely.

______________________________________________________________________

### Claude Code (CLI)

Add to your project's `.mcp.json` or `~/.claude/mcp_servers.json`:

```json
{
  "mcpServers": {
    "qubinode-airflow": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://YOUR_SERVER:8889/sse", "--header", "X-API-Key:YOUR_API_KEY"]
    },
    "qubinode-ai": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "http://YOUR_SERVER:8081/sse", "--header", "X-API-Key:YOUR_API_KEY"]
    }
  }
}
```

Or configure via CLI:

```bash
claude mcp add qubinode-airflow --transport sse --url "http://YOUR_SERVER:8889/sse"
```

______________________________________________________________________

### Cursor IDE

Add to Cursor's MCP settings (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "qubinode": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "http://YOUR_SERVER:8889/sse",
        "--header",
        "X-API-Key:YOUR_API_KEY"
      ]
    }
  }
}
```

______________________________________________________________________

### Continue.dev

Add to `~/.continue/config.json`:

```json
{
  "experimental": {
    "modelContextProtocolServers": [
      {
        "transport": {
          "type": "sse",
          "url": "http://YOUR_SERVER:8889/sse",
          "headers": {
            "X-API-Key": "YOUR_API_KEY"
          }
        }
      }
    ]
  }
}
```

______________________________________________________________________

### Custom Python Client

Using the official MCP Python SDK:

```python
import asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

async def connect_to_qubinode():
    """Connect to Qubinode MCP server."""

    url = "http://YOUR_SERVER:8889/sse"
    headers = {"X-API-Key": "YOUR_API_KEY"}

    async with sse_client(url, headers=headers) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize connection
            await session.initialize()

            # List available tools
            tools = await session.list_tools()
            print(f"Available tools: {[t.name for t in tools.tools]}")

            # Call a tool
            result = await session.call_tool("list_dags", {})
            print(f"DAGs: {result.content}")

            # Call VM listing
            vms = await session.call_tool("list_vms", {})
            print(f"VMs: {vms.content}")

if __name__ == "__main__":
    asyncio.run(connect_to_qubinode())
```

**Install dependencies:**

```bash
pip install mcp httpx-sse
```

______________________________________________________________________

### Custom Node.js Client

Using `@modelcontextprotocol/sdk`:

```javascript
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { SSEClientTransport } from "@modelcontextprotocol/sdk/client/sse.js";

async function main() {
  const transport = new SSEClientTransport(
    new URL("http://YOUR_SERVER:8889/sse"),
    {
      requestInit: {
        headers: {
          "X-API-Key": "YOUR_API_KEY"
        }
      }
    }
  );

  const client = new Client({
    name: "my-qubinode-client",
    version: "1.0.0"
  }, {
    capabilities: {}
  });

  await client.connect(transport);

  // List tools
  const tools = await client.listTools();
  console.log("Available tools:", tools.tools.map(t => t.name));

  // Call a tool
  const result = await client.callTool({
    name: "list_dags",
    arguments: {}
  });
  console.log("DAGs:", result.content);

  await client.close();
}

main().catch(console.error);
```

**Install dependencies:**

```bash
npm install @modelcontextprotocol/sdk
```

______________________________________________________________________

## Tool Reference

### DAG Management (3 tools)

| Tool           | Description                                       | Parameters                        |
| -------------- | ------------------------------------------------- | --------------------------------- |
| `list_dags`    | List all Airflow DAGs with schedules and metadata | None                              |
| `get_dag_info` | Get detailed info about a specific DAG            | `dag_id: string`                  |
| `trigger_dag`  | Execute a DAG with optional config                | `dag_id: string`, `conf?: object` |

### VM Operations (5 tools)

| Tool                    | Description                                                                                 | Parameters                                                                        |
| ----------------------- | ------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| `list_vms`              | List all VMs managed by kcli/virsh                                                          | None                                                                              |
| `get_vm_info`           | Get details about a specific VM                                                             | `vm_name: string`                                                                 |
| `create_vm`             | Create a new VM                                                                             | `name: string`, `image?: string`, `memory?: int`, `cpus?: int`, `disk_size?: int` |
| `delete_vm`             | Delete a VM                                                                                 | `name: string`                                                                    |
| `preflight_vm_creation` | **CALL BEFORE create_vm** - Validates resources, checks image availability, ensures success | `name: string`, `image?: string`, `memory?: int`, `cpus?: int`, `disk_size?: int` |

### RAG Operations (6 tools)

| Tool                       | Description                       | Parameters                                                                    |
| -------------------------- | --------------------------------- | ----------------------------------------------------------------------------- |
| `query_rag`                | Semantic search in knowledge base | `query: string`, `doc_types?: list`, `limit?: int`, `threshold?: float`       |
| `ingest_to_rag`            | Add documents to RAG              | `content: string`, `doc_type: string`, `source?: string`, `metadata?: object` |
| `manage_rag_documents`     | Manage document ingestion         | `operation: string`, `params?: object`                                        |
| `get_rag_stats`            | Get RAG statistics                | None                                                                          |
| `compute_confidence_score` | Assess task confidence            | `task_description: string`, `doc_types?: list`                                |
| `check_provider_exists`    | Check for Airflow provider        | `system_name: string`                                                         |

### Troubleshooting (2 tools)

| Tool                          | Description                   | Parameters                                                                                           |
| ----------------------------- | ----------------------------- | ---------------------------------------------------------------------------------------------------- |
| `get_troubleshooting_history` | Retrieve past solutions       | `error_pattern?: string`, `component?: string`, `only_successful?: bool`, `limit?: int`              |
| `log_troubleshooting_attempt` | Log a troubleshooting attempt | `task: string`, `solution: string`, `result: string`, `error_message?: string`, `component?: string` |

### Lineage (4 tools)

| Tool                       | Description                     | Parameters                           |
| -------------------------- | ------------------------------- | ------------------------------------ |
| `get_dag_lineage`          | Get DAG dependencies            | `dag_id: string`, `depth?: int`      |
| `get_failure_blast_radius` | Analyze failure impact          | `dag_id: string`, `task_id?: string` |
| `get_dataset_lineage`      | Get dataset producers/consumers | `dataset_name: string`               |
| `get_lineage_stats`        | Get lineage system stats        | None                                 |

### System (2 tools)

| Tool                 | Description                   | Parameters |
| -------------------- | ----------------------------- | ---------- |
| `get_airflow_status` | Get Airflow health status     | None       |
| `get_system_info`    | Get comprehensive system info | None       |

### Workflow Orchestration (2 tools) - NEW

These tools dramatically improve multi-step operation success rates by providing structured guidance.

| Tool                 | Description                                                                                  | Parameters                                                                                      |
| -------------------- | -------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- |
| `get_workflow_guide` | **CALL FIRST for multi-step tasks** - Returns step-by-step execution plan with tool sequence | `workflow_type?: string`, `goal_description?: string`                                           |
| `diagnose_issue`     | Structured troubleshooting with component-specific diagnostic checks                         | `symptom: string`, `component?: string`, `error_message?: string`, `affected_resource?: string` |

**Available workflow types:**

- `create_openshift_cluster` - Full OpenShift deployment (45-90 min)
- `setup_freeipa` - FreeIPA identity management (20-30 min)
- `deploy_vm_basic` - Simple VM creation with validation (5-10 min)
- `troubleshoot_vm` - Systematic VM troubleshooting (10-20 min)

______________________________________________________________________

## LLM Interaction Patterns

### Pattern 1: Discovery First

Always start by understanding the system:

```
1. Call get_system_info() to understand capabilities
2. Call get_airflow_status() to verify system health
3. Call list_dags() to see available workflows
4. Call list_vms() to see existing infrastructure
```

### Pattern 2: Check Before Acting

Before modifying infrastructure:

```
1. Call compute_confidence_score(task_description)
   - If < 0.6: STOP and request documentation
   - If >= 0.6: Proceed with caution
   - If >= 0.8: Proceed confidently

2. Call get_troubleshooting_history(error_pattern)
   - Check if similar issues were solved before

3. Call check_provider_exists(system_name)
   - Use native providers instead of BashOperator
```

### Pattern 3: Learn From Failures

After any operation:

```
1. If successful:
   log_troubleshooting_attempt(task, solution, "success")

2. If failed:
   log_troubleshooting_attempt(task, solution, "failed", error_message)
   get_troubleshooting_history(error_message) # Check for solutions
```

### Pattern 4: VM Lifecycle (High Success Rate)

**IMPORTANT:** Always use `preflight_vm_creation()` before `create_vm()` for 80%+ success rate:

```
1. list_vms() → Check existing VMs and naming conventions
2. preflight_vm_creation(name, cpus=4, memory=8192, disk_size=50)
   → If any check fails: FIX FIRST before proceeding
   → Shows: memory available, disk space, image status, libvirt health
3. create_vm(name, cpus=4, memory=8192, disk_size=50)
4. get_vm_info(name) → Verify creation
5. [Do operations via DAGs]
6. delete_vm(name) → Cleanup when done
7. log_troubleshooting_attempt() → Record for future reference
```

### Pattern 5: Lineage Awareness

Before retrying failed tasks:

```
1. get_failure_blast_radius(dag_id, task_id)
   - Understand downstream impact
   - Check severity rating

2. If severity is HIGH:
   - Get human approval before retrying
   - Consider partial recovery strategies
```

### Pattern 6: Multi-Step Workflows (80%+ Success Rate)

**NEW:** Use `get_workflow_guide()` for complex operations:

```
1. get_workflow_guide(workflow_type="deploy_vm_basic")
   OR
   get_workflow_guide(goal_description="I need to deploy OpenShift")

   → Returns ordered steps with exact tool calls
   → Shows required vs optional steps
   → Includes failure recovery guidance

2. Follow the returned steps IN ORDER
   → Each step shows the exact tool call to make
   → Required steps must pass before continuing

3. If any step fails:
   diagnose_issue(symptom="<what went wrong>", component="<vm|dag|network>")
   → Gets component-specific diagnostic checks
   → Links to historical solutions

4. After completion:
   log_troubleshooting_attempt(task, solution, "success")
```

### Pattern 7: Structured Troubleshooting (80%+ Success Rate)

**NEW:** Use `diagnose_issue()` for systematic problem resolution:

```
1. diagnose_issue(
     symptom="VM won't boot",
     component="vm",
     error_message="libvirt error code 1",
     affected_resource="my-test-vm"
   )

2. Follow the diagnostic plan in order:
   - Step 1: Check historical solutions
   - Step 2: Search knowledge base
   - Step 3: Run component-specific checks

3. When resolved:
   log_troubleshooting_attempt(task, solution, "success", component="vm")
   → Builds knowledge base for future issues
```

______________________________________________________________________

## Authentication

### Generating API Keys

API keys are generated during setup:

```bash
cd /opt/qubinode_navigator/airflow
./setup-mcp-servers.sh
```

Or generate manually:

```bash
# Generate a secure key
openssl rand -hex 32

# Add to environment
export AIRFLOW_MCP_API_KEY="your-generated-key"
export MCP_API_KEY="your-generated-key"
```

### Key Storage

Keys are stored in:

- `/opt/qubinode_navigator/airflow/.env.mcp`
- Environment variables in docker-compose.yml

### Security Best Practices

1. **Never commit keys to git** - Use `.env` files or secrets management
1. **Rotate keys regularly** - Regenerate every 90 days
1. **Use read-only mode in production** - Set `AIRFLOW_MCP_TOOLS_READ_ONLY=true`
1. **Restrict network access** - Only expose MCP ports to trusted networks

______________________________________________________________________

## Troubleshooting

### Connection Issues

```bash
# Check if server is running
curl http://YOUR_SERVER:8889/health

# Expected response:
# {"status": "healthy", "features": {...}}

# Check with API key
curl -H "X-API-Key: YOUR_KEY" http://YOUR_SERVER:8889/sse
```

### Tools Not Appearing

1. Verify server is running: `podman ps | grep mcp`
1. Check logs: `podman logs airflow_airflow-mcp-server_1`
1. Restart client completely (Claude Desktop, Cursor, etc.)
1. Verify API key is correct

### Permission Errors

If tools return permission errors:

```bash
# Check read-only mode
grep READ_ONLY /opt/qubinode_navigator/airflow/.env

# Disable read-only for write operations
export AIRFLOW_MCP_TOOLS_READ_ONLY=false
```

### SSE Connection Drops

If connections drop frequently:

1. Check server logs for errors
1. Increase timeout in client config
1. Verify network stability between client and server

______________________________________________________________________

## Quick Reference

### Endpoints

| Service          | SSE Endpoint             | Health Check                |
| ---------------- | ------------------------ | --------------------------- |
| Airflow MCP      | `http://SERVER:8889/sse` | `http://SERVER:8889/health` |
| AI Assistant MCP | `http://SERVER:8081/sse` | `http://SERVER:8081/health` |

### Environment Variables

```bash
# Airflow MCP Server
AIRFLOW_MCP_ENABLED=true
AIRFLOW_MCP_PORT=8889
AIRFLOW_MCP_API_KEY=<key>
AIRFLOW_MCP_TOOLS_READ_ONLY=false

# AI Assistant MCP Server
MCP_SERVER_ENABLED=true
MCP_SERVER_PORT=8081
MCP_API_KEY=<key>
```

### Test Commands

After configuring your client, try these prompts:

```
1. "List all available Airflow workflows"
2. "Show me the running VMs"
3. "Search documentation for kcli usage"
4. "What's the confidence score for deploying FreeIPA?"
5. "Create a test VM with 2 CPUs and 4GB RAM"
```

______________________________________________________________________

## Support

- **Documentation**: `docs/MCP-SERVER-DESIGN.md`
- **Quick Start**: `MCP-QUICK-START.md`
- **Issues**: [GitHub Issues](https://github.com/Qubinode/qubinode_navigator/issues)
- **ADR Reference**: `docs/adrs/adr-0038-fastmcp-framework-migration.md`

______________________________________________________________________

*Last Updated: December 2025*
