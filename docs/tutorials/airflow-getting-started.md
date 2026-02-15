---
title: Airflow Getting Started
parent: Tutorials
nav_order: 2
---

# Getting Started with Apache Airflow for Qubinode Navigator

> **Documentation status**
>
> - Validation: `IN PROGRESS` – Based on `deploy-qubinode-with-airflow.sh` and current Airflow sidecar configuration.
> - Last reviewed: 2025-11-21
> - Community: If you use this tutorial to bring up Airflow and run Qubinode DAGs, please share fixes or enhancements via [Contributing to docs](../how-to/contribute.md).

This tutorial shows how to:

1. Deploy Qubinode Navigator **together with Apache Airflow and nginx** using `deploy-qubinode-with-airflow.sh`.
1. Access the Airflow UI through nginx.
1. Locate and run Qubinode-related DAGs.

______________________________________________________________________

## 1. Prerequisites

- A host where Qubinode Navigator can run (RHEL 9/10, CentOS Stream 9/10, Rocky Linux 9, etc.).
- Container runtime and networking set up per your platform guide.
- Platform-specific inventory and environment files prepared as described in:
  - [Deploying on Hetzner](../deployments/demo-hetzner-com.markdown)
  - [Deploying on Red Hat Product Demo System](../deployments/demo-redhat-com.markdown)
- Ports 80/443 available for nginx.

If you havent done a base deployment yet, start with:

- [Deploy To Production](../how-to/deploy-to-production.md)

______________________________________________________________________

## 2. Run `deploy-qubinode-with-airflow.sh`

On the prepared host:

```bash
cd /opt/qubinode_navigator    # or your clone path

./deploy-qubinode-with-airflow.sh
```

The script will:

- Run the base Qubinode deployment (if needed).
- Deploy Apache Airflow using the existing configuration.
- Configure nginx as a reverse proxy in front of Airflow and the AI Assistant.
- Close direct ports (e.g., 8888/8080) and expose only 80/443.

At the end, you should see output similar to:

```text
✓ Direct ports 8888/8080 closed
✓ Access only through nginx (port 80/443)
✓ Ready for SSL/TLS configuration

📚 Next Steps:
   1. Access Airflow UI and enable example DAGs
   2. Test kcli and virsh operators
   3. Chat with AI Assistant for guidance
```

If the script fails, review the logs it prints and update this tutorial with any repeatable troubleshooting steps you discover.

______________________________________________________________________

## 3. Access the Airflow UI

Once deployment completes successfully:

1. Determine the host IP:
   ```bash
   hostname -I | awk '{print $1}'
   ```
1. In a browser, open:
   - `http://YOUR_HOST_IP/` (served by nginx as the Airflow UI).
1. Log in with the credentials configured for Airflow (often `admin` / `admin` by default e change immediately for production).

nginx is configured to:

- Proxy `/` to the Airflow webserver.
- Proxy `/ai/` (or similar) to the AI Assistant API (depending on your nginx config in `deploy-qubinode-with-airflow.sh`).

______________________________________________________________________

## 4. Locate and Run Qubinode DAGs

In the Airflow UI:

1. Go to **DAGs** view.
1. Look for DAGs related to Qubinode Navigator, for example (exact names may vary by version):
   - `qubinode_simple_deploy`
   - `multi_cloud_deploy`
   - RAG/AI‑related workflows documented in:
     - [Airflow Integration Guide](../airflow-integration-guide.md)
     - [DAG Deployment Workflows](../airflow-dag-deployment-workflows.md)

To run a DAG:

1. Unpause it if it is paused.
1. Use the **Play** button to trigger a run.
1. Monitor the tasks in the **Graph** or **Tree** view and inspect logs when needed.

______________________________________________________________________

## 5. Integrate with the AI Assistant

With Airflow and the AI Assistant running behind nginx:

- You can use the AI Assistant to:
  - Trigger DAGs via natural language requests.
  - Ask for status of specific workflows.
  - Query documentation or RAG‑powered answers about deployment issues.

See also:

- [Airflow Community Ecosystem](../airflow-community-ecosystem.md)
- [Airflow ↔ RAG Bidirectional Learning](../airflow-rag-bidirectional-learning.md)

______________________________________________________________________

## 6. Next Steps and Contributions

- If you adopt additional DAGs or customize workflows, consider contributing:
  - New example DAGs.
  - Small sections here describing your common patterns.
- If you run into repeated issues (e.g., firewall, SELinux, SSL termination), add a **Troubleshooting** section to this tutorial so future users benefit from your findings.
