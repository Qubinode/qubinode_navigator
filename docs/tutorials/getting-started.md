---
title: Getting Started
parent: Tutorials
nav_order: 1
---

# Getting Started

This tutorial walks you from zero to a running Qubinode Navigator deployment with Airflow, AI Assistant, and VM provisioning capabilities.

**Estimated time**: 15-25 minutes

## Prerequisites

Before you begin, ensure you have:

- **OS**: RHEL 9/10, CentOS Stream 10, Rocky Linux 9+, or Fedora 39+
- **RAM**: 8GB minimum (16GB+ recommended)
- **Disk**: 50GB+ free space
- **CPU**: Virtualization enabled (VT-x/AMD-V)
- **Software**: Git, Podman (or Docker)
- **Network**: Internet access for container images

## Step 1: Clone the Repository

```bash
# Install git if not present
sudo dnf install -y git

# Clone the repository
git clone https://github.com/Qubinode/qubinode_navigator.git
cd qubinode_navigator
```

## Step 2: Run Pre-flight Checks

The preflight script validates your system and auto-fixes common issues:

```bash
./scripts/preflight-check.sh --fix
```

**What it checks:**

- CPU virtualization support
- Container runtime (podman)
- Network connectivity
- Disk space and memory
- Required external repositories

If all checks pass, you'll see:

```
Pre-flight checks passed!
You can proceed with deployment.
```

## Step 3: Deploy the Full Stack

For a full deployment with Airflow orchestration and the AI Assistant:

```bash
sudo -E ./scripts/development/deploy-qubinode.sh
```

This deploys:

- **Apache Airflow** (workflow orchestration) on port 8888
- **AI Assistant** (PydanticAI orchestrator + RAG) on port 8080
- **MCP Server** (tool API for LLM integration) on port 8889
- **PostgreSQL** (metadata + pgvector) on port 5432

## Step 4: Verify the Deployment

Check that all services are running:

```bash
# Check container status
sudo podman ps

# Verify Airflow
curl http://localhost:8888/health

# Verify AI Assistant
curl http://localhost:8080/orchestrator/status
```

## Step 5: Access the Services

| Service          | URL                   | Purpose                             |
| ---------------- | --------------------- | ----------------------------------- |
| **Airflow UI**   | `http://YOUR_IP:8888` | DAG management and monitoring       |
| **AI Assistant** | `http://YOUR_IP:8080` | Chat-driven deployment orchestrator |
| **MCP Server**   | `http://YOUR_IP:8889` | Tool API for LLM integration        |

## Step 6: Run Your First DAG

1. Open the Airflow UI at `http://YOUR_IP:8888`
1. You'll see pre-built DAGs:

| DAG                            | Purpose                              |
| ------------------------------ | ------------------------------------ |
| `infrastructure_health_check`  | Monitor infrastructure components    |
| `example_kcli_vm_provisioning` | Create/manage VMs with kcli          |
| `freeipa_deployment`           | Deploy FreeIPA identity management   |
| `stepca_deployment`            | Deploy Step-CA certificate authority |

3. **Enable a DAG**: Click the toggle switch
1. **Trigger a DAG**: Click the "play" button
1. **Monitor**: Watch progress in Graph or Grid view

Start with `infrastructure_health_check` to verify everything is working.

## Troubleshooting

### Containers not starting

```bash
# Check logs for a specific service
cd airflow && podman-compose logs -f

# Restart all services
cd airflow && podman-compose restart
```

### Pre-flight check failures

```bash
# Run with verbose output
./scripts/preflight-check.sh --fix 2>&1 | tee preflight.log

# Common fixes:
# - Enable virtualization in BIOS
# - Start libvirtd: systemctl start libvirtd
# - Install podman: dnf install -y podman podman-compose
```

### VM operations failing

```bash
# Verify kcli is working on the host
sudo kcli list vm

# Check if libvirtd is running
systemctl status libvirtd
```

## Next Steps

- [Airflow Getting Started](./airflow-getting-started.md) - Deep dive into DAG management
- [MCP Production Setup](./mcp-production-and-client.md) - Configure MCP for production
- [Deploy to Production](../how-to/deploy-to-production.md) - Production best practices
- [Architecture Overview](../explanation/architecture-overview.md) - Understand the design
