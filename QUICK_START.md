# Qubinode Navigator Quick Start Guide

## 🚀 One-Shot Deployment for RHEL-Based Systems

Deploy a complete Qubinode Navigator solution on any RHEL-based machine with a single command!

### 📋 Prerequisites

- **Operating System**: RHEL 8/9/10, CentOS Stream, Rocky Linux, or AlmaLinux
- **Hardware**: 8GB+ RAM, 50GB+ disk space, VT-x/AMD-V support
- **Access**: Root privileges, internet connectivity
- **Time**: 15-30 minutes for complete deployment

### ⚡ Quick Deployment (3 Steps)

#### 1. Configure Environment

```bash
# Copy the example configuration
cp .env.example .env

# Edit with your settings
vi .env
```

**Minimum required configuration:**

```bash
QUBINODE_DOMAIN=your-domain.com
QUBINODE_ADMIN_USER=admin
QUBINODE_CLUSTER_NAME=mycluster
```

#### 2. Run Deployment

```bash
# Deploy with AI Assistant support
# Note: deploy-qubinode.sh is a symlink to scripts/development/deploy-qubinode.sh
./deploy-qubinode.sh

# For full stack with Airflow orchestration, use instead:
# ./deploy-qubinode-with-airflow.sh
```

#### 3. Access Your Cluster

After successful deployment:

- **AI Assistant**: http://localhost:8080 (for troubleshooting help)
- **Cluster Management**: `/opt/qubinode-navigator`
- **Virtual Machines**: `virsh list --all`

### 🤖 AI Assistant Integration

The deployment includes an **AI Assistant** that can help with:

- **Real-time troubleshooting** during deployment
- **Configuration guidance** and best practices
- **Error resolution** with context-aware suggestions
- **Post-deployment** cluster management help

If you encounter issues, the AI Assistant will automatically provide guidance!

### 📊 Deployment Modes

| Mode            | Use Case          | Features                          |
| --------------- | ----------------- | --------------------------------- |
| **development** | Local dev/testing | Debug tools, relaxed security     |
| **staging**     | Pre-production    | Production-like, testing features |
| **production**  | Live workloads    | Full security, monitoring, HA     |

### 🔧 Advanced Configuration

#### Environment Variables

```bash
# Resource Configuration
export QUBINODE_STORAGE_SIZE=200Gi
export QUBINODE_WORKER_NODES=5

# Feature Flags
export QUBINODE_ENABLE_MONITORING=true
export QUBINODE_ENABLE_LOGGING=true
export QUBINODE_ENABLE_AI_ASSISTANT=true

# Run deployment
./deploy-qubinode.sh
```

#### Cloud Provider Support

**AWS Example:**

```bash
export QUBINODE_DOMAIN=cluster.aws.company.com
export AWS_REGION=us-west-2
export AWS_ACCESS_KEY_ID=AKIA...
export AWS_SECRET_ACCESS_KEY=...
./deploy-qubinode.sh
```

**Hetzner Cloud Example:**

```bash
export QUBINODE_DOMAIN=cluster.hetzner.company.com
export HETZNER_TOKEN=your_token
./deploy-qubinode.sh
```

### 🛠️ Troubleshooting

#### Common Issues & Solutions

**1. Hardware Virtualization Not Supported**

```bash
# Check CPU support
grep -E '(vmx|svm)' /proc/cpuinfo

# Enable in BIOS/UEFI if not shown
# Look for: Intel VT-x, AMD-V, Virtualization Technology
```

**2. Insufficient Resources**

```bash
# Check current resources
free -h        # Memory
df -h          # Disk space

# Minimum requirements: 8GB RAM, 50GB disk
```

**3. Network Connectivity Issues**

```bash
# Test connectivity
ping 8.8.8.8
curl -I https://quay.io

# Check DNS resolution
nslookup github.com
```

**4. Package Installation Failures**

```bash
# Update package cache
dnf clean all
dnf makecache

# Check repository configuration
dnf repolist
```

#### AI Assistant Help

If the AI Assistant is running, you can get contextual help:

```bash
# Check AI Assistant status
curl http://localhost:8080/health

# Access web interface
firefox http://localhost:8080
```

The AI Assistant provides:

- **Error analysis** with specific solutions
- **System diagnostics** and recommendations
- **Best practices** for your environment
- **Step-by-step guidance** for complex issues

### 📁 File Structure

After deployment:

```
/opt/qubinode-navigator/
├── deploy-qubinode.sh          # One-shot deployment script
├── .env                        # Your configuration
├── .env.example               # Configuration template
├── setup.sh                   # Main setup script
├── rhel9-linux-hypervisor.sh  # RHEL 9 specific setup
├── config/                     # Configuration files
├── plugins/                    # Plugin system
├── ai-assistant/              # AI Assistant components
└── docs/                      # Documentation
```

### 🔍 Verification Commands

```bash
# Check hypervisor status
virsh list --all
systemctl status libvirtd

# Check AI Assistant
curl http://localhost:8080/health
podman ps | grep ai-assistant

# Check system resources
free -h
df -h
lscpu | grep -i virtual
```

### 📚 Next Steps

1. **Explore the AI Assistant**: Visit http://localhost:8080
1. **Deploy workloads**: Use the cluster management tools
1. **Monitor resources**: Check system and cluster metrics
1. **Scale up**: Add more nodes or resources as needed
1. **Get help**: Ask the AI Assistant for guidance

### 🆘 Getting Help

1. **AI Assistant**: http://localhost:8080 (primary support)
1. **Deployment Logs**: Check `/tmp/qubinode-deployment-*.log`
1. **System Logs**: `journalctl -u libvirtd -f`
1. **Community**: GitHub issues and discussions

### 📚 Related Documentation

- **[README.md](README.md)** - Project overview and all deployment options
- **[QUICKSTART.md](QUICKSTART.md)** - Full stack deployment with Airflow
- **[GETTING_STARTED.md](docs/GETTING_STARTED.md)** - Development deployment guide
- **[CLEAN-INSTALL-GUIDE.md](docs/CLEAN-INSTALL-GUIDE.md)** - This guide (detailed)
- **[AGENTS.md](AGENTS.md)** - AI coding agent instructions

### 🎯 Success Indicators

✅ **Deployment Successful** when you see:

- "DEPLOYMENT COMPLETED" message
- AI Assistant accessible at http://localhost:8080
- `virsh list` shows available domains
- No critical errors in deployment log

### 🔄 Redeployment

To redeploy or fix issues:

```bash
# Clean up previous deployment
./deploy-qubinode.sh --cleanup  # (if available)

# Or manually clean
podman stop qubinode-ai-assistant
podman rm qubinode-ai-assistant

# Redeploy
./deploy-qubinode.sh
```

______________________________________________________________________

## 🎉 Welcome to Qubinode Navigator!

Your RHEL-based infrastructure platform is ready. The AI Assistant is standing by to help with any questions or issues you encounter.

**Happy clustering!** 🚀
