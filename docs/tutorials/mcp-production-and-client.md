---
title: MCP Production & Client Setup
parent: Tutorials
nav_order: 3
---

# MCP Production Deployment & Client Setup

> **Documentation status**
>
> - Validation: `IN PROGRESS` – Optimized for `deploy-fastmcp-production.sh` and current MCP server layout.
> - Last reviewed: 2025-11-21
> - Community: If you run this tutorial successfully (or hit issues), please update it via [Contributing to docs](../how-to/contribute.md).

This tutorial walks you through:

1. Deploying the **MCP services** (Airflow MCP server + AI Assistant MCP server) using `deploy-fastmcp-production.sh`.
1. Verifying that the MCP endpoints are up.
1. Connecting an MCP-compatible client (for example, **Claude Desktop**) to those services.

______________________________________________________________________

## 1. Prerequisites

Before you start, ensure:

- **Host OS**: RHEL 9/10, CentOS Stream 9/10, Rocky Linux 9, or similar.
- **Container runtime**: `podman` and `podman-compose` (or aliases correctly configured).
- **Ports**:
  - Airflow MCP server and AI Assistant MCP server ports are reachable from your client machine.
- **Repository**: `qubinode_navigator` checked out on the host.

If you havent already deployed the base Qubinode environment, see:

- [Deploy To Production](../how-to/deploy-to-production.md)

______________________________________________________________________

## 2. Deploy MCP Services with `deploy-fastmcp-production.sh`

On the host where `qubinode_navigator` is cloned:

```bash
cd /opt/qubinode_navigator  # or the path where you cloned the repo

./deploy-fastmcp-production.sh
```

This script will:

- Stop any existing MCP profile services via `podman-compose --profile mcp down`.
- Start the **MCP profile** via `podman-compose --profile mcp up -d`.
- Wait for the **Airflow MCP server** container to be reported as `Up`.

Watch the output for a line similar to:

```text
✓ Airflow MCP server is up
```

If the script exits with an error, inspect the logs (for example, `podman-compose logs` in the appropriate directory) and update this tutorial with any troubleshooting steps you discover.

______________________________________________________________________

## 3. Verify MCP Endpoints

Once the containers are running, verify that the MCP endpoints are reachable.

Typical checks (adapt as needed to match your configuration):

```bash
# From the host running the containers

# Check Airflow MCP SSE endpoint (port and path may vary based on config)
curl -N http://localhost:8889/sse || echo "Airflow MCP SSE check failed"

# Check AI Assistant MCP SSE endpoint
curl -N http://localhost:8080/sse || echo "AI Assistant MCP SSE check failed"
```

Also confirm that the containers are running:

```bash
podman ps
# or
podman-compose --profile mcp ps
```

You should see entries for the MCP-related containers (for example, an Airflow MCP server container and an AI Assistant MCP container).

______________________________________________________________________

## 4. Configure an MCP Client (Claude Desktop Example)

Qubinode Navigator ships with an example MCP client configuration for Claude Desktop.

Relevant files:

- `claude_desktop_config.json` at the repo root.

### 4.1 Locate and review the example config

Open `claude_desktop_config.json` in your editor and note:

- The MCP server URLs (hostnames/ports) for:
  - Airflow MCP server.
  - AI Assistant MCP server.
- Any authentication or security settings (if configured).

Ensure the hostnames and ports match your environment (for example, `localhost` vs. a remote IP).

### 4.2 Apply configuration to Claude Desktop

On the machine where Claude Desktop is installed:

1. Open the Claude Desktop configuration directory (typically `~/.config/claude/` on Linux).
1. Back up any existing `claude_desktop_config.json`.
1. Copy or merge the MCP configuration from the Qubinode Navigator `claude_desktop_config.json`.
1. Adjust:
   - Hostnames (e.g., replace `YOUR_SERVER_IP` with the actual host IP of the MCP services).
   - Ports, if you changed them.

Restart Claude Desktop after updating the configuration.

______________________________________________________________________

## 5. Test MCP Tools from the Client

Once Claude Desktop (or another MCP client) is configured:

1. Start a new chat.
1. Confirm that the MCP tools are detected (you should see tools for Airflow operations and documentation/AI Assistant operations).
1. Try simple actions, such as:
   - Listing Airflow DAGs.
   - Querying deployment status.
   - Asking the AI Assistant to search Qubinode documentation.

Explore the MCP tools available in Claude Desktop by typing `/` in the chat to see the available commands and capabilities.

______________________________________________________________________

## 6. Contribute Improvements

If you complete this tutorial and notice missing details or differences in your environment:

- Update this tutorial via a pull request, or
- File an issue describing:
  - Your environment (OS, container runtime, ports).
  - Any changes you needed (e.g., different ports, additional health endpoints).

This will help keep the MCP documentation accurate and production-ready over time.
