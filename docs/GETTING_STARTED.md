# Getting Started with Qubinode Navigator

**From zero to running infrastructure in 15 minutes**

This guide helps you deploy and understand the Qubinode Navigator platform, including its AI-powered orchestration capabilities demonstrated in our automated E2E tests.

## What is Qubinode Navigator?

Qubinode Navigator is an **AI-enhanced, container-first infrastructure automation platform** that provides:

- **AI Orchestrator**: Natural language infrastructure deployment ("Deploy FreeIPA for me")
- **Apache Airflow**: DAG-based workflow orchestration with visual monitoring
- **kcli Integration**: VM provisioning and management
- **Multi-Cloud Support**: Deploy to local KVM, AWS, GCP, Azure, Equinix, Hetzner

## Quick Start (3 Commands)

```bash
# 1. Clone and enter the repository
git clone https://github.com/Qubinode/qubinode_navigator.git
cd qubinode_navigator

# 2. Run pre-flight checks (validates and fixes your system)
./scripts/preflight-check.sh --fix

# 3. Deploy everything (AI Assistant + Airflow + PostgreSQL)
sudo -E ./scripts/development/deploy-qubinode.sh
```

**Total time**: 15-25 minutes

> **Deployment Options**: This guide uses the development deployment script. For a full production stack with Airflow + Marquez + Nginx, use `./deploy-qubinode-with-airflow.sh` instead. See [README.md](../README.md#choose-your-deployment-method) for all deployment options.
>
> **Note**: `deploy-qubinode.sh` in the repo root is a symlink to `scripts/development/deploy-qubinode.sh`.

> **Note**: This is the same deployment method used in our [E2E CI workflow](https://github.com/Qubinode/qubinode_navigator/actions) which runs on CentOS Stream 10.

## Prerequisites

| Requirement | Minimum                                   | Recommended      |
| ----------- | ----------------------------------------- | ---------------- |
| **OS**      | RHEL 9, CentOS Stream 9/10, Rocky Linux 9 | CentOS Stream 10 |
| **RAM**     | 8GB                                       | 16GB+            |
| **Disk**    | 50 GB                                     | 100 GB+          |
| **CPU**     | VT-x/AMD-V enabled                        | 4+ cores         |
| **Network** | Internet access                           | Static IP        |

### Verify Prerequisites

```bash
# Check virtualization support
grep -E '(vmx|svm)' /proc/cpuinfo

# Check memory
free -h

# Check disk space
df -h

# Check OS version
cat /etc/redhat-release
```

## What Gets Deployed

After running `./scripts/development/deploy-qubinode.sh`, you'll have:

| Service          | URL                 | Purpose                              |
| ---------------- | ------------------- | ------------------------------------ |
| **AI Assistant** | http://YOUR_IP:8080 | RAG-powered chat + Orchestrator API  |
| **Airflow UI**   | http://YOUR_IP:8888 | Workflow monitoring & DAG management |
| **PostgreSQL**   | localhost:5432      | Airflow metadata database            |

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interfaces                          │
│   ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│   │ Terminal/CLI │  │ Airflow UI   │  │ AI Chat Interface  │   │
│   │   (kcli)     │  │   (:8888)    │  │      (:8080)       │   │
│   └──────────────┘  └──────────────┘  └────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AI Orchestrator Layer                         │
│   ┌────────────────────────────────────────────────────────┐    │
│   │  /orchestrator/intent - Natural Language Processing    │    │
│   │  "Deploy FreeIPA" → DAG Selection → Execution         │    │
│   └────────────────────────────────────────────────────────┘    │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Apache Airflow Layer                          │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐    │
│   │  Scheduler  │  │  Webserver  │  │   PostgreSQL DB     │    │
│   └─────────────┘  └─────────────┘  └─────────────────────┘    │
│                                                                  │
│   Pre-built DAGs:                                                │
│   • freeipa_deployment    • stepca_deployment                    │
│   • vyos_router_deployment • ocp_initial_deployment              │
│   • harbor_deployment      • infrastructure_health_check         │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Infrastructure Layer                          │
│   ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐    │
│   │    kcli     │  │   libvirt   │  │    Ansible          │    │
│   │  (VM mgmt)  │  │   (KVM)     │  │  (Configuration)    │    │
│   └─────────────┘  └─────────────┘  └─────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Environment Configuration

Before deployment, you can customize behavior with environment variables:

```bash
# Required for AI features - at least one provider
export OPENROUTER_API_KEY=sk-or-...   # Recommended - multiple models

# Deployment settings
export QUBINODE_DOMAIN=your-domain.local
export QUBINODE_ADMIN_USER=admin
export QUBINODE_CLUSTER_NAME=qubinode
export QUBINODE_DEPLOYMENT_MODE=production

# Feature flags
export QUBINODE_ENABLE_AI_ASSISTANT=true
export QUBINODE_ENABLE_AIRFLOW=true
export BUILD_AI_ASSISTANT_FROM_SOURCE=true  # For latest features
export USE_LOCAL_MODEL=false  # Skip local llama.cpp model download

# Then deploy
sudo -E ./scripts/development/deploy-qubinode.sh
```

> **CI Environment**: Our E2E tests use `USE_LOCAL_MODEL=false` to skip the 2-5 minute model download and rely on cloud APIs via the PydanticAI orchestrator.

## Using the AI Orchestrator

The AI Orchestrator translates natural language requests into infrastructure actions.

### Example: Deploy FreeIPA

```bash
# Via curl (as used in our E2E tests)
curl -X POST http://localhost:8080/orchestrator/intent \
  -H "Content-Type: application/json" \
  -d '{
    "intent": "Deploy FreeIPA server for identity management",
    "params": {"vm_name": "freeipa", "action": "create"},
    "auto_approve": true,
    "auto_execute": true
  }'
```

**Response:**

```json
{
  "flow_id": "flow-a41656cbe5b6",
  "status": "in_progress",
  "dag_id": "freeipa_deployment",
  "execution_id": "exec-f53066a77455",
  "phases_completed": ["dag_discovery", "dag_validation", "dag_execution"],
  "airflow_ui_url": "http://localhost:8888/dags/freeipa_deployment/grid"
}
```

### Monitoring Deployments

Use the Observer Agent to track progress:

```bash
# Check deployment status
curl -X POST "http://localhost:8080/orchestrator/observe?dag_id=freeipa_deployment"
```

**Response includes:**

- `overall_status`: running, success, failed, pending
- `progress_percent`: 0-100
- `recommendations`: AI-generated next steps
- `concerns`: Warnings or errors detected

## Available DAGs (Workflows)

| DAG ID                        | Purpose               | Deploys                  |
| ----------------------------- | --------------------- | ------------------------ |
| `freeipa_deployment`          | Identity management   | FreeIPA server with DNS  |
| `stepca_deployment`           | Certificate authority | Step-CA for internal PKI |
| `vyos_router_deployment`      | Network routing       | VyOS router VM           |
| `harbor_deployment`           | Container registry    | Harbor registry          |
| `ocp_initial_deployment`      | OpenShift cluster     | OCP 4.x cluster          |
| `infrastructure_health_check` | System validation     | Health reports           |

### Triggering DAGs Manually

**Via Airflow UI:**

1. Open http://YOUR_IP:8888
1. Find your DAG in the list
1. Click the toggle to enable it (DAGs are paused by default)
1. Click "Play" → "Trigger DAG"

**Via CLI:**

```bash
# Unpause a DAG first (required)
sudo podman exec airflow-scheduler \
  airflow dags unpause freeipa_deployment

# Trigger a DAG
sudo podman exec airflow-scheduler \
  airflow dags trigger freeipa_deployment

# Check DAG run status
sudo podman exec airflow-scheduler \
  airflow dags list-runs -d freeipa_deployment --limit 1
```

## Verifying Your Deployment

### Check Services

```bash
# Check all containers are running
sudo podman ps

# Expected output:
# airflow-scheduler    Up
# airflow-webserver    Up
# airflow-postgres     Up
# qubinode-ai-assistant Up
```

### Check VM Infrastructure

```bash
# List VMs (requires sudo for root-owned VMs)
sudo kcli list vm

# Check libvirt service
systemctl status libvirtd
```

### Health Endpoints

```bash
# AI Assistant health
curl http://localhost:8080/health

# Orchestrator status (shows API keys configured)
curl http://localhost:8080/orchestrator/status

# DAG discovery
curl http://localhost:8080/orchestrator/dags
```

## SSH Configuration for Airflow

Airflow containers execute kcli/Ansible commands on the host via SSH. The deployment script configures this automatically, but you can verify:

```bash
# Test SSH from container perspective
sudo ssh -o StrictHostKeyChecking=no root@localhost "echo 'SSH OK'"

# Verify authorized_keys
cat /root/.ssh/authorized_keys
```

This pattern is documented in [ADR-0043](./adrs/adr-0043-airflow-container-host-network-access.md) and [ADR-0046](./adrs/adr-0046-dag-validation-pipeline-and-host-execution.md).

## Running as Non-Root User (Recommended)

If you prefer not to run as root, you can create a dedicated `lab-user` with sudo privileges:

### Create the lab-user

```bash
# Download and run the user creation script
curl -OL https://gist.githubusercontent.com/tosin2013/385054f345ff7129df6167631156fa2a/raw/b67866c8d0ec220c393ea83d2c7056f33c472e65/configure-sudo-user.sh
chmod +x configure-sudo-user.sh
./configure-sudo-user.sh lab-user
```

### Configure SSH for lab-user

```bash
# Switch to lab-user
sudo su - lab-user

# Generate SSH key
ssh-keygen -f ~/.ssh/id_rsa -t rsa -N ''

# Copy key to localhost for Airflow container access
IP_ADDRESS=$(hostname -I | awk '{print $1}')
ssh-copy-id lab-user@${IP_ADDRESS}

# Verify SSH works
ssh lab-user@${IP_ADDRESS} "echo 'SSH OK'"
```

### Configure Environment Variables

When running as `lab-user`, set these environment variables to use the correct paths:

```bash
# Add to ~/.bashrc or export before deployment
export QUBINODE_SSH_USER=lab-user
export QUBINODE_SSH_KEY_PATH=~/.ssh/id_rsa
export QUBINODE_INVENTORY_DIR=~/.generated
export QUBINODE_VAULT_PASSWORD_FILE=~/.vault_password
```

### Deploy as lab-user

```bash
# Clone repository
git clone https://github.com/Qubinode/qubinode_navigator.git
cd qubinode_navigator

# Run pre-flight checks
./scripts/preflight-check.sh --fix

# Deploy (sudo -E preserves environment variables)
sudo -E ./scripts/development/deploy-qubinode.sh
```

> **Note**: The DAG helper functions automatically detect the current user via `QUBINODE_SSH_USER` environment variable or fall back to the `USER` environment variable. See [Issue #122](https://github.com/Qubinode/qubinode_navigator/issues/122) for details on the configurable user support.

## Troubleshooting

### DAG Not Appearing in Airflow

```bash
# Check for import errors
sudo podman exec airflow-scheduler \
  airflow dags list-import-errors

# Force DAG rescan
sudo podman exec airflow-scheduler \
  airflow dags reserialize
```

### VM Operations Failing

```bash
# Check kcli is working (use sudo!)
sudo kcli list vm

# Verify libvirt is running
systemctl status libvirtd

# Test SSH for Airflow container
sudo ssh -o StrictHostKeyChecking=no root@localhost "kcli list vm"
```

### Container Logs

```bash
# AI Assistant logs
sudo podman logs qubinode-ai-assistant --tail 50

# Airflow scheduler logs
sudo podman logs airflow-scheduler --tail 50

# All Airflow logs
cd airflow && sudo podman-compose logs -f
```

### Observer Agent Returns "pending"

The Observer Agent returns "pending" status when no DAG runs exist:

```json
{"overall_status": "pending", "summary": "No DAG runs found for freeipa_deployment"}
```

This is normal before triggering a DAG. Unpause and trigger the DAG first, then observe.

## CLI Quick Reference

```bash
# --- Deployment ---
./scripts/preflight-check.sh --fix           # Validate system
sudo -E ./scripts/development/deploy-qubinode.sh  # Deploy everything

# --- Airflow ---
cd airflow && sudo podman-compose ps         # Check status
cd airflow && sudo podman-compose logs -f    # View logs
cd airflow && sudo podman-compose down       # Stop all
cd airflow && sudo podman-compose up -d      # Start all

# --- DAG Management ---
sudo podman exec airflow-scheduler airflow dags list
sudo podman exec airflow-scheduler airflow dags unpause <dag_id>
sudo podman exec airflow-scheduler airflow dags trigger <dag_id>
sudo podman exec airflow-scheduler airflow dags list-runs -d <dag_id>

# --- VMs (use sudo!) ---
sudo kcli list vm                            # List VMs
sudo kcli info vm <name>                     # VM details
sudo kcli delete vm <name> -y                # Delete VM

# --- AI Orchestrator ---
curl http://localhost:8080/orchestrator/status
curl http://localhost:8080/orchestrator/dags
curl -X POST http://localhost:8080/orchestrator/intent \
  -H "Content-Type: application/json" \
  -d '{"intent": "your request", "auto_execute": true}'
```

## Next Steps

1. **Explore the Airflow UI**: http://YOUR_IP:8888

   - Review pre-built DAGs
   - Check task dependencies in Graph view

1. **Try the AI Chat**: http://YOUR_IP:8080

   - Ask questions about infrastructure
   - Request deployments in natural language

1. **Deploy Your First VM**:

   ```bash
   sudo kcli create vm test-vm -i centos9stream
   ```

1. **Read the ADRs**: `docs/adrs/` contains architecture decisions

1. **Customize DAGs**: `airflow/dags/` - create your own workflows

## Documentation Index

| Document                                           | Description                   |
| -------------------------------------------------- | ----------------------------- |
| [CLEAN-INSTALL-GUIDE.md](./CLEAN-INSTALL-GUIDE.md) | Fresh OS installation         |
| [AIRFLOW-INTEGRATION.md](./AIRFLOW-INTEGRATION.md) | Airflow setup details         |
| [MCP-SERVER-DESIGN.md](./MCP-SERVER-DESIGN.md)     | MCP server architecture       |
| [docs/adrs/](./adrs/)                              | Architecture Decision Records |

## Getting Help

- **AI Assistant**: http://YOUR_IP:8080 (chat interface)
- **Documentation**: https://qubinode.github.io/qubinode_navigator/
- **Issues**: https://github.com/Qubinode/qubinode_navigator/issues
- **ADRs**: `docs/adrs/` - design decisions and rationale

______________________________________________________________________

**Tested with**: CentOS Stream 10, Kernel 6.12.0, E2E CI workflow
**Last Updated**: December 2025
