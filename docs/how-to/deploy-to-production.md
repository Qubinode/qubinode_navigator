---
title: Deploy To Production
parent: How to
nav_order: 1
---

# Deploy To Production

> **Documentation status**
>
> - Validation: `IN PROGRESS` – This how-to summarizes the current recommended path for production deployments.
> - Last reviewed: 2025-11-21
> - Community: If you run this end to end, please update this page via [Contributing to docs](./contribute.md).

## What "production" means here

This guide is for taking a **tested Qubinode Navigator deployment** into a production-style environment:

- A single-node KVM hypervisor host prepared with Qubinode Navigator.
- Environment-specific deployment (Hetzner / Red Hat Demo / other bare metal) completed using the platform guides.
- Optional Apache Airflow + AI Assistant for orchestration.

## Prerequisites

- Supported OS: RHEL 8/9/10, CentOS Stream 10, Rocky Linux, or Fedora.
- SSH access with sudo/root privileges.
- Sufficient CPU, RAM, and disk as per the platform guides.
- DNS / domain ready if exposing public endpoints.
- Review these docs first:
  - [Clean Install Guide](https://github.com/Qubinode/qubinode_navigator/blob/main/docs/CLEAN-INSTALL-GUIDE.md)
  - [Unified Deployment Guide](https://github.com/Qubinode/qubinode_navigator/blob/main/docs/UNIFIED-DEPLOYMENT-GUIDE.md)
  - [Deployment Integration Guide](https://github.com/Qubinode/qubinode_navigator/blob/main/docs/DEPLOYMENT_INTEGRATION_GUIDE.md)

## Step 1 – Prepare the host

1. Follow the **Clean Install Guide** to bring the host to a known-good baseline.
1. Verify:
   - KVM / virtualization is enabled and working.
   - Network interfaces and storage layout match the chosen deployment guide.

## Step 2 – Choose a deployment path

Use the platform-specific guides on GitHub:

- **Hetzner**: [Deploying on Hetzner](https://github.com/Qubinode/qubinode_navigator/blob/main/docs/deployments/demo-hetzner-com.markdown)
- **Red Hat Product Demo System**: [Deploying on Red Hat Product Demo System](https://github.com/Qubinode/qubinode_navigator/blob/main/docs/deployments/demo-redhat-com.markdown)
- **Other bare metal**: Use the appropriate deployment guide for your environment.

These guides describe how to configure `notouch.env`, `/tmp/config.yml`, and other environment variables for non-interactive deployments.

## Step 3 – Run the production deployment script

On the prepared host, the primary production entry point is:

```bash
git clone https://github.com/Qubinode/qubinode_navigator.git
cd qubinode_navigator

./deploy-qubinode-with-airflow.sh
```

- Ensure your `.env` / `notouch.env` / `/tmp/config.yml` are configured as described in the deployment guides.
- Confirm that the script completes successfully and nginx/Airflow are up.

> **Note for developers:** other scripts such as `setup_modernized.sh` and `deploy-qubinode.sh` exist for framework and legacy flows, but end‑user production deployments should prefer `deploy-qubinode-with-airflow.sh`.

## Step 4 – Optional: enable Airflow orchestration

If you want production-style workflow orchestration and chat-driven operations:

- Read:
  - [Airflow Integration Overview](https://github.com/Qubinode/qubinode_navigator/blob/main/docs/AIRFLOW-INTEGRATION.md)
  - [DAG Deployment Workflows](https://github.com/Qubinode/qubinode_navigator/blob/main/docs/airflow-dag-deployment-workflows.md)
  - [Airflow Community Ecosystem](https://github.com/Qubinode/qubinode_navigator/blob/main/docs/airflow-community-ecosystem.md)

Then:

1. Enable Airflow via the documented environment variables.
1. Deploy the Airflow sidecar and example DAGs.
1. Integrate with the AI Assistant for chat-based workflow management.
1. To deploy the MCP services (Airflow MCP server + AI Assistant) for MCP clients (e.g. Claude Desktop), run:

```bash
cd /opt/qubinode_navigator
./deploy-fastmcp-production.sh
```

Ensure `podman-compose` is installed and your MCP configuration matches the MCP documentation.

## Step 5 – Verify and monitor

Use the existing production verification docs to confirm your deployment:

At minimum, verify:

- Hypervisor services (KVM/libvirt, Cockpit, SSH) are healthy.
- Qubinode Navigator workflows complete without errors.
- Airflow UI is reachable at port 8888.
- AI Assistant endpoint is responsive at port 8080.

```bash
# Check container status
sudo podman ps

# Verify Airflow health
curl http://localhost:8888/health

# Verify AI Assistant
curl http://localhost:8080/orchestrator/status
```

## Troubleshooting

If you encounter issues:

- Check container logs: `cd airflow && podman-compose logs -f`
- Restart services: `cd airflow && podman-compose restart`
- Re-run preflight checks: `./scripts/preflight-check.sh --fix`

## Related Guides

- [Getting Started Tutorial](../tutorials/getting-started.md)
- [Airflow Getting Started](../tutorials/airflow-getting-started.md)
- [Reference Documentation](../reference/)
