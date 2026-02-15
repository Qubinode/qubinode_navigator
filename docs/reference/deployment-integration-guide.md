---
title: Deployment Integration Guide
parent: Reference
nav_order: 2
---

# Deployment Integration Guide

## 🎯 **Overview**

This guide explains how the new **one-shot deployment script** (`deploy-qubinode.sh`) integrates with existing Qubinode Navigator deployment patterns and documentation.

## 📋 **Research Findings**

Based on analysis of `docs/deployments/demo-hetzner-com.markdown` and `docs/deployments/demo-redhat-com.markdown`, we identified three primary deployment patterns:

### **1. Hetzner Cloud Deployment**

- **Target OS**: Rocky Linux 9
- **Script**: `rocky-linux-hetzner.sh`
- **Inventory**: `hetzner`
- **Domain Pattern**: `qubinodelab.io`
- **Network**: `FORWARDER=1.1.1.1`, `INTERFACE=bond0`

### **2. Red Hat Demo System (Equinix Metal)**

- **Target OS**: RHEL 9
- **Script**: `rhel9-linux-hypervisor.sh`
- **Inventory**: `rhel9-equinix`
- **Domain Pattern**: `sandbox000.opentlc.com`
- **Network**: Auto-detect forwarder, `INTERFACE=bond0`

### **3. Local Development**

- **Target OS**: Any supported RHEL-based system
- **Script**: `setup.sh` → `rhel9-linux-hypervisor.sh`
- **Inventory**: `localhost`
- **Domain Pattern**: `dev.local`
- **Network**: Auto-detect interface and DNS

## 🔄 **Integration Strategy**

Our one-shot deployment script (`deploy-qubinode.sh`) **preserves and enhances** the existing architecture:

### **Compatibility Layer**

1. **Automatic Target Detection**: Detects deployment target based on domain patterns and inventory settings
1. **notouch.env Generation**: Creates compatible `notouch.env` file for existing scripts
1. **Function Integration**: Reuses proven functions from `setup.sh`
1. **Inventory Compatibility**: Works with existing inventory configurations

### **Enhanced Features**

1. **AI Assistant Integration**: Real-time troubleshooting and guidance
1. **Modern OS Support**: RHEL 9/10, CentOS Stream 9/10, Rocky 9, Alma 9
1. **Intelligent Configuration**: Auto-detects network settings and deployment patterns
1. **Comprehensive Logging**: Structured logging with error context

## 🛠️ **Configuration Mapping**

### **Environment Variables Compatibility**

| Existing Pattern              | One-Shot Script                  | Purpose                     |
| ----------------------------- | -------------------------------- | --------------------------- |
| `SSH_USER=lab-user`           | `SSH_USER=lab-user`              | SSH user configuration      |
| `CICD_PIPELINE='true'`        | `CICD_PIPELINE=true`             | CI/CD mode enablement       |
| `ENV_USERNAME=lab-user`       | `ENV_USERNAME=$SSH_USER`         | Environment username        |
| `DOMAIN=qubinodelab.io`       | `QUBINODE_DOMAIN=qubinodelab.io` | Domain configuration        |
| `INVENTORY=hetzner`           | `INVENTORY=hetzner`              | Ansible inventory selection |
| `FORWARDER='1.1.1.1'`         | `FORWARDER=1.1.1.1`              | DNS forwarder               |
| `INTERFACE=bond0`             | `INTERFACE=bond0`                | Network interface           |
| `USE_HASHICORP_VAULT='false'` | `USE_HASHICORP_VAULT=false`      | Vault integration           |

### **Deployment Target Detection**

The script automatically detects deployment targets:

```bash
# Hetzner Detection
if [[ "$QUBINODE_DOMAIN" =~ "hetzner" || "$QUBINODE_DOMAIN" =~ "qubinodelab.io" ]]; then
    DEPLOYMENT_TARGET="hetzner"
    INVENTORY="hetzner"
    FORWARDER="1.1.1.1"
fi

# Equinix Detection
if [[ "$QUBINODE_DOMAIN" =~ "opentlc.com" || "$INVENTORY" == "rhel9-equinix" ]]; then
    DEPLOYMENT_TARGET="equinix"
    INVENTORY="rhel9-equinix"
    FORWARDER="$(awk '/^nameserver/ {print $2}' /etc/resolv.conf | head -1)"
fi

# Local Development Detection
if [[ "$QUBINODE_DOMAIN" =~ "dev.local" || "$INVENTORY" == "localhost" ]]; then
    DEPLOYMENT_TARGET="local"
    INVENTORY="localhost"
fi
```

## 📁 **File Structure Integration**

### **Configuration Files**

```
/opt/qubinode_navigator/
├── .env                    # New: One-shot script configuration
├── .env.example           # New: Configuration template with deployment examples
├── notouch.env            # Generated: Compatibility with existing scripts
├── deploy-qubinode.sh     # New: One-shot deployment script
├── setup.sh               # Existing: Generic setup (still used internally)
├── rhel9-linux-hypervisor.sh  # Existing: RHEL 9 deployment (still used internally)
└── rocky-linux-hetzner.sh     # Existing: Rocky Linux deployment (still used internally)
```

### **Inventory Integration**

```
inventories/
├── localhost/             # Local development
├── hetzner/              # Hetzner Cloud deployments
├── rhel9-equinix/        # Red Hat Demo System
├── dev/                  # Development environment
└── sample/               # Sample configuration
```

## 🚀 **Migration Path**

### **From Existing Deployments**

**1. Hetzner Cloud Users:**

```bash
# OLD WAY (demo-hetzner-com.markdown)
curl -OL https://raw.githubusercontent.com/Qubinode/qubinode_navigator/main/rocky-linux-hetzner.sh
chmod +x rocky-linux-hetzner.sh
source notouch.env && sudo -E ./rocky-linux-hetzner.sh

# NEW WAY (one-shot script)
cp .env.example .env
# Edit .env with Hetzner-specific settings
./deploy-qubinode.sh
```

**2. Red Hat Demo System Users:**

```bash
# OLD WAY (demo-redhat-com.markdown)
curl -OL https://raw.githubusercontent.com/Qubinode/qubinode_navigator/main/rhel9-linux-hypervisor.sh
chmod +x rhel9-linux-hypervisor.sh
source notouch.env && sudo -E ./rhel9-linux-hypervisor.sh

# NEW WAY (one-shot script)
cp .env.example .env
# Edit .env with Equinix-specific settings
./deploy-qubinode.sh
```

### **Configuration Examples**

**Hetzner Cloud (.env):**

```bash
QUBINODE_DOMAIN=qubinodelab.io
QUBINODE_ADMIN_USER=lab-user
QUBINODE_CLUSTER_NAME=hetzner-cluster
INVENTORY=hetzner
SSH_USER=lab-user
FORWARDER=1.1.1.1
INTERFACE=bond0
USE_ROUTE53=true
```

**Red Hat Demo System (.env):**

```bash
QUBINODE_DOMAIN=sandbox000.opentlc.com
QUBINODE_ADMIN_USER=lab-user
QUBINODE_CLUSTER_NAME=rhel9-equinix-cluster
INVENTORY=rhel9-equinix
SSH_USER=lab-user
INTERFACE=bond0
USE_ROUTE53=true
```

## 🔧 **Advanced Integration Features**

### **1. Credential Management**

- **Existing**: Manual `/tmp/config.yml` creation
- **Enhanced**: AI Assistant guides credential setup
- **Compatible**: Still supports `/tmp/config.yml` pattern

### **2. HashiCorp Vault Integration**

- **Existing**: Manual HCP Vault setup
- **Enhanced**: Automated vault configuration
- **Compatible**: Preserves existing vault workflows

### **3. Network Configuration**

- **Existing**: Manual interface detection
- **Enhanced**: Automatic interface detection with fallbacks
- **Compatible**: Respects existing network settings

### **4. Error Handling**

- **Existing**: Manual troubleshooting
- **Enhanced**: AI Assistant provides contextual help
- **Compatible**: Maintains existing error patterns

## 📊 **Deployment Workflow Comparison**

### **Traditional Multi-Step Process**

```
1. SSH into server
2. Create lab-user (configure-sudo-user.sh)
3. Create /tmp/config.yml manually
4. Create notouch.env manually
5. Download specific deployment script
6. Run deployment script
7. Manual troubleshooting if issues occur
```

### **One-Shot Deployment Process**

```
1. SSH into server
2. Configure .env file (with examples and guidance)
3. Run ./deploy-qubinode.sh
4. AI Assistant provides help if issues occur
```

## 🎯 **Benefits**

### **For Users**

- **Simplified Process**: Single command deployment
- **Intelligent Guidance**: AI Assistant for troubleshooting
- **Automatic Detection**: No manual target configuration
- **Modern OS Support**: Latest RHEL-based systems

### **For Maintainers**

- **Preserved Architecture**: Existing scripts still work
- **Enhanced Compatibility**: Automatic notouch.env generation
- **Centralized Logic**: Single entry point with consistent patterns
- **Future-Proof**: Easy to extend for new deployment targets

## 🔄 **Backward Compatibility**

The one-shot script **maintains full backward compatibility**:

1. **Existing Scripts Work**: `setup.sh`, `rhel9-linux-hypervisor.sh`, etc. still function
1. **Configuration Preserved**: `notouch.env` automatically generated
1. **Inventory Compatible**: Works with all existing inventories
1. **Function Reuse**: Leverages proven functions from existing scripts

## 🚀 **Future Enhancements**

### **Planned Features**

1. **Multi-Architecture Support**: ARM64 compatibility
1. **Cloud Integration**: Enhanced cloud provider support
1. **Container Orchestration**: Kubernetes/OpenShift deployment
1. **Monitoring Integration**: Built-in observability

### **Extension Points**

1. **New Deployment Targets**: Easy to add new cloud providers
1. **Custom Workflows**: Pluggable deployment steps
1. **Integration APIs**: REST API for programmatic deployment
1. **Advanced AI Features**: Predictive troubleshooting

______________________________________________________________________

## 📞 **Support**

- **AI Assistant**: Available during deployment for real-time help
- **Documentation**: Comprehensive guides and examples
- **Community**: GitHub issues and discussions
- **Enterprise**: Professional support available

The one-shot deployment script represents the **evolution** of Qubinode Navigator deployment, providing a **modern, intelligent, and user-friendly** experience while **preserving the robust architecture** that users depend on.
