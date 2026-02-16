---
title: API Documentation
parent: Reference
nav_order: 1
---

# API Documentation

> **Documentation status**
>
> - Validation: `IN PROGRESS` – This page summarizes the main APIs and integrations exposed by Qubinode Navigator.
> - Last reviewed: 2025-11-21
> - Community: If you rely on a specific API or discover missing details, please help improve this page via [Contributing to docs](../how-to/contribute.md).

This page is an index of the **main APIs and integration surfaces** used with Qubinode Navigator. Detailed behavior and examples are documented in the linked pages.

## 1. Infrastructure Deployment Entry Points

These are the **recommended production entry points**:

- `./deploy-qubinode-with-airflow.sh` – Unified deployment for Qubinode Navigator **plus** Apache Airflow and nginx reverse proxy.
- `./deploy-fastmcp-production.sh` – Deploys MCP services only (Airflow MCP server + AI Assistant) using `podman-compose --profile mcp`.

Platform-specific preconfiguration (inventory, `notouch.env`, `/tmp/config.yml`) is documented under `../deployments/`.

### Developer / legacy scripts

The following scripts are primarily for **developers** and historical workflows (now located under `scripts/development/`):

- `scripts/development/setup_modernized.sh` – Modern plugin-based setup script for the core Navigator.
- `scripts/development/setup.sh` – Legacy setup script (compatibility mode).
- `scripts/development/deploy-qubinode.sh` – Older one-shot Qubinode deployment script (hypervisor + Navigator, no Airflow/nginx stack).

See also:

- [Unified Deployment Guide](../how-to/unified-deployment-guide.md)
- [Deployment Integration Guide](./deployment-integration-guide.md)

## 2. AI Assistant REST API

The AI Assistant container exposes a REST API used for health checks and AI-powered operations.

Key characteristics (see [AI Assistant Deployment Strategy](../explanation/ai-assistant-deployment-strategy.md)):

- Default image: `quay.io/takinosh/qubinode-ai-assistant:latest`.
- Default port: `8080` (container) – typically mapped to a host port.
- Health endpoint:

```bash
curl http://localhost:8080/health
```

Additional endpoints and request/response formats are defined in the AI Assistant service code and may evolve over time. For implementation details, refer to the `ai-assistant/` sources and deployment strategy document above.

## 3. MCP Servers (Model Context Protocol)

Qubinode Navigator ships with MCP servers to expose infrastructure and documentation tools to LLM clients.

High-level documentation:

- See [MCP Production & Client Setup Tutorial](../tutorials/mcp-production-and-client.md) for deployment guide
- See [ADR-0038: FastMCP Framework Migration](https://github.com/Qubinode/qubinode_navigator/blob/main/docs/adrs/adr-0038-fastmcp-framework-migration.md) for implementation details

These cover:

- **Airflow MCP Server** – tools for DAG management and VM operations.
- **AI Assistant MCP Server** – tools for RAG-powered doc search and chat.
- Configuration for Claude Desktop and other MCP-compatible clients.

## 4. Apache Airflow Integration API

The project integrates with **Apache Airflow 2.x** using Airflow's standard REST API and DAG interfaces.

Reference docs:

- [Airflow Integration Overview](../explanation/airflow-integration.md)
- [Airflow Integration Guide](../tutorials/airflow-integration-guide.md)
- [DAG Deployment Workflows](./airflow-dag-deployment-workflows.md)

From an API perspective:

- Airflow's own REST API is used for:
  - Triggering DAG runs.
  - Inspecting run status.
  - Listing available workflows.
- Qubinode-specific examples and code snippets are provided in the integration and workflow guides above. For full endpoint semantics, see the official Airflow API documentation.

## 5. CLI and Plugin Framework

The **plugin framework CLI** is the main command-line API for interacting with Qubinode Navigator plugins:

```bash
# List available plugins
python3 qubinode_cli.py list

# Deploy with a specific OS plugin
python3 qubinode_cli.py deploy --plugin rhel10

# Get plugin information
python3 qubinode_cli.py info --plugin centos_stream10
```

Additional CLI behavior and plugin options are documented throughout the deployment and development guides. Future iterations may add a dedicated CLI reference page under `docs/reference/`.

______________________________________________________________________

If you need deeper, per-endpoint details for any of the above, please open an issue or contribute examples to this page so it can evolve alongside the platform.

**Response:**

```json
{
  "field1": "value",
  "field2": 123
}
```

### POST /api/resource

Creates...

## Configuration Options

| Option  | Type    | Default   | Description            |
| ------- | ------- | --------- | ---------------------- |
| option1 | string  | "default" | Description of option1 |
| option2 | boolean | false     | Description of option2 |

## Error Codes

| Code | Description       | Resolution |
| ---- | ----------------- | ---------- |
| E001 | Error description | How to fix |
| E002 | Error description | How to fix |
