# Qubinode Navigator - Quick Start Guide

**Get from zero to running infrastructure in 15 minutes**

## Prerequisites

- **OS**: RHEL 9, CentOS Stream 9, Rocky Linux 9, or Fedora 39+
- **RAM**: 8GB minimum (16GB+ recommended)
- **Disk**: 50GB+ free space
- **CPU**: Virtualization enabled (VT-x/AMD-V)
- **Network**: Internet access for container images

## Step 1: Clone the Repository (2 min)

```bash
# Install git if not present
sudo dnf install -y git

# Clone the repository
git clone https://github.com/Qubinode/qubinode_navigator.git
cd qubinode_navigator
```

## Step 2: Run Pre-flight Checks (2 min)

This validates your system and auto-fixes common issues:

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
You can proceed with deployment:
  ./deploy-qubinode-with-airflow.sh
```

## Step 3: Deploy Everything (10-15 min)

```bash
./deploy-qubinode-with-airflow.sh
```

This script deploys:

- Apache Airflow (workflow orchestration)
- PostgreSQL (Airflow metadata database)
- AI Assistant (optional)
- Nginx reverse proxy
- SSH configuration for container→host access

## Step 4: Access the Services

After deployment completes, you'll see:

| Service          | URL                   | Credentials   |
| ---------------- | --------------------- | ------------- |
| **Airflow UI**   | http://YOUR_IP/       | admin / admin |
| **AI Assistant** | http://YOUR_IP/ai/    | (no auth)     |
| **Health Check** | http://YOUR_IP/health | (no auth)     |

## Step 5: Enable and Run DAGs

1. Open Airflow UI in your browser
1. You'll see several pre-built DAGs:

| DAG                            | Purpose                              |
| ------------------------------ | ------------------------------------ |
| `example_kcli_vm_provisioning` | Create/manage VMs with kcli          |
| `infrastructure_health_check`  | Monitor infrastructure components    |
| `freeipa_deployment`           | Deploy FreeIPA identity management   |
| `stepca_deployment`            | Deploy Step-CA certificate authority |
| `certificate_provisioning`     | Request/renew TLS certificates       |
| `dns_management`               | Manage DNS records in FreeIPA        |

3. **Enable a DAG**: Click the toggle switch to enable it
1. **Run a DAG**: Click the "play" button → "Trigger DAG"
1. **Monitor**: Watch progress in Graph or Grid view

## Recommended First DAGs

### 1. Test Infrastructure Health

```
DAG: infrastructure_health_check
Purpose: Verify all components are working
Action: Trigger manually
```

### 2. Create Your First VM

```
DAG: example_kcli_vm_provisioning
Purpose: Create a CentOS Stream 10 VM
Action: Trigger with default parameters
```

### 3. Deploy FreeIPA (Identity Management)

```
DAG: freeipa_deployment
Purpose: Deploy FreeIPA for DNS + identity
Action: Configure parameters, then trigger
```

## Command Reference

```bash
# Check deployment status
./airflow/deploy-airflow.sh status

# View container logs
cd airflow && podman-compose logs -f

# Restart services
cd airflow && podman-compose restart

# Stop everything
cd airflow && podman-compose down

# Start everything
cd airflow && podman-compose up -d
```

## Directory Structure

```
qubinode_navigator/
├── airflow/
│   ├── dags/                    # Workflow definitions (DAGs)
│   ├── plugins/qubinode/        # Custom operators for kcli, virsh
│   ├── docker-compose.yml       # Container configuration
│   └── deploy-airflow.sh        # Deployment script
├── scripts/
│   ├── preflight-check.sh       # Pre-deployment validation
│   ├── qubinode-cert            # Certificate management CLI
│   └── qubinode-dns             # DNS management CLI
├── ansible/
│   └── roles/                   # Ansible roles for deployments
└── docs/
    └── adrs/                    # Architecture Decision Records
```

## Troubleshooting

### Airflow UI not accessible

```bash
# Check if containers are running
cd airflow && podman-compose ps

# Check logs
podman-compose logs airflow-webserver
```

### DAG not appearing

```bash
# Check scheduler logs
cd airflow && podman-compose logs airflow-scheduler

# Force DAG rescan
podman-compose restart airflow-scheduler
```

### VM operations failing

```bash
# Verify kcli is working on the host
kcli list vm

# Check if libvirtd is running
systemctl status libvirtd
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

## Next Steps

1. **Deploy FreeIPA** - Identity management with DNS
1. **Deploy Step-CA** - Internal certificate authority
1. **Deploy VyOS** - Network segmentation (requires console access)
1. **Create custom DAGs** - Automate your infrastructure

## Getting Help

- **Documentation**: `docs/` directory
- **ADRs**: `docs/adrs/` - Architecture decisions
- **AI Assistant**: Chat at http://YOUR_IP/ai/
- **Issues**: https://github.com/Qubinode/qubinode_navigator/issues

## Related Documentation

- **[README.md](README.md)** - Project overview and all deployment options
- **[GETTING_STARTED.md](docs/GETTING_STARTED.md)** - Development deployment guide
- **[CLEAN-INSTALL-GUIDE.md](docs/CLEAN-INSTALL-GUIDE.md)** - Complete installation from scratch
- **[AGENTS.md](AGENTS.md)** - AI coding agent instructions
- **[MCP-SERVER-GUIDE.md](MCP-SERVER-GUIDE.md)** - MCP server setup

______________________________________________________________________

**Estimated total time**: 15-25 minutes from clone to running Airflow UI
