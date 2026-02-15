---
title: Clean Installation Guide
parent: How to
nav_order: 6
---

# Qubinode Navigator - Clean Installation Guide

## 🎯 For New Users Starting from a Clean Operating System

This guide provides step-by-step instructions for installing Qubinode Navigator on a fresh RHEL-based system.

## 📋 Prerequisites

### **Supported Operating Systems**

- ✅ **RHEL 9.x or 10.x** (Red Hat Enterprise Linux)
- ✅ **CentOS Stream 9 or 10**
- ✅ **Rocky Linux 9.x**
- ✅ **AlmaLinux 9.x**

### **System Requirements**

- **Memory**: Minimum 8GB RAM (16GB+ recommended)
- **Storage**: Minimum 50GB free disk space (100GB+ recommended)
- **CPU**: Hardware virtualization support (VT-x/AMD-V)
- **Network**: Internet connectivity for package downloads
- **User**: Root access or sudo privileges

### **Hardware Verification**

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

## 🚀 Quick Start (Recommended)

### **Step 1: Download and Run**

```bash
# Clone the repository
git clone https://github.com/Qubinode/qubinode_navigator.git
cd qubinode_navigator

# Configure environment (edit with your settings)
cp .env.example .env

# Run pre-flight checks
./scripts/preflight-check.sh --fix

# Deploy full stack with Airflow orchestration (recommended)
./deploy-qubinode-with-airflow.sh

# OR: Deploy core components only
# Note: deploy-qubinode.sh is a symlink to scripts/development/deploy-qubinode.sh
# sudo ./deploy-qubinode.sh
```

That's it! The script will:

- ✅ Auto-detect your operating system
- ✅ Auto-configure DNS settings
- ✅ Install all required packages
- ✅ Set up KVM virtualization
- ✅ Configure networking and storage
- ✅ Start the AI Assistant (optional)

## 📝 Custom Configuration (Optional)

### **Step 1: Create Configuration File**

```bash
# Copy the example configuration
cp .env.example .env

# Edit with your settings
vim .env
```

### **Step 2: Minimum Required Configuration**

```bash
# Required settings in .env file
QUBINODE_DOMAIN=your-domain.local
QUBINODE_ADMIN_USER=your-username
QUBINODE_CLUSTER_NAME=your-cluster-name
```

### **Step 3: Optional Settings**

```bash
# Deployment mode (development, staging, production)
QUBINODE_DEPLOYMENT_MODE=production

# AI Assistant (true/false)
QUBINODE_ENABLE_AI_ASSISTANT=true

# KVM version
KVM_VERSION=0.10.4
```

## 🌐 Environment-Specific Configurations

### **Local Development**

```bash
# .env configuration for local development
QUBINODE_DOMAIN=dev.local
QUBINODE_ADMIN_USER=developer
QUBINODE_CLUSTER_NAME=dev-cluster
QUBINODE_DEPLOYMENT_MODE=development
INVENTORY=localhost
```

### **Hetzner Cloud**

```bash
# .env configuration for Hetzner Cloud
QUBINODE_DOMAIN=your-domain.com
QUBINODE_ADMIN_USER=lab-user
QUBINODE_CLUSTER_NAME=hetzner-cluster
INVENTORY=hetzner
```

### **Red Hat Demo System (Equinix)**

```bash
# .env configuration for Red Hat Demo System
QUBINODE_DOMAIN=sandbox000.opentlc.com
QUBINODE_ADMIN_USER=lab-user
QUBINODE_CLUSTER_NAME=rhel9-cluster
INVENTORY=rhel9-equinix
```

## 🔧 Manual Installation (Advanced Users)

### **Step 1: System Preparation**

```bash
# Update system
sudo dnf update -y

# Install git
sudo dnf install -y git

# Clone repository
git clone https://github.com/Qubinode/qubinode_navigator.git
cd qubinode_navigator
```

### **Step 2: Configure Environment**

```bash
# Create configuration
cp .env.example .env
vim .env  # Edit with your settings
```

### **Step 3: Run Deployment**

```bash
# Make script executable
chmod +x deploy-qubinode.sh

# Run deployment
sudo ./deploy-qubinode.sh
```

## 🔍 Verification Steps

### **After Deployment Completes**

```bash
# Check libvirt service
sudo systemctl status libvirtd

# Check DNS configuration
cat /etc/resolv.conf

# List virtual networks
sudo virsh net-list --all

# Check available storage pools
sudo virsh pool-list --all

# Test virtualization
sudo virt-host-validate
```

### **Expected Results**

```bash
✅ libvirtd: active (running)
✅ DNS: Real nameservers (not "CHANGEME")
✅ Networks: qubinet network available
✅ Storage: default pool available
✅ Virtualization: All checks pass
```

## 🆘 Troubleshooting

### **Common Issues and Solutions**

#### **Issue: "RHEL 8 is no longer supported"**

**Solution**: Upgrade to RHEL 9 or 10

```bash
# Check current version
cat /etc/redhat-release

# Upgrade guide available at:
# https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/9/html/upgrading_from_rhel_8_to_rhel_9/index
```

#### **Issue: "No internet connectivity detected"**

**Solution**: Check network configuration

```bash
# Test connectivity
ping 8.8.8.8

# Check DNS resolution
nslookup google.com

# Check network interface
ip route show default
```

#### **Issue: "Insufficient resources"**

**Solution**: Check system resources

```bash
# Check memory
free -h

# Check disk space
df -h

# Check CPU virtualization
grep -E '(vmx|svm)' /proc/cpuinfo
```

#### **Issue: "Package installation failed"**

**Solution**: Check repositories and subscriptions

```bash
# For RHEL systems, ensure subscription is active
sudo subscription-manager status

# Update package cache
sudo dnf clean all && sudo dnf makecache

# Try manual package installation
sudo dnf install -y git vim wget
```

#### **Issue: "Ansible collection installation failed"**

**Solution**: Check Python and Ansible setup

```bash
# Check Python version
python3 --version

# Check Ansible installation
ansible --version

# Reinstall if needed
sudo pip3 install ansible-navigator
```

## 🤖 AI Assistant Usage

If enabled, the AI Assistant provides intelligent help:

### **Access the AI Assistant**

```bash
# Check if running
curl http://localhost:8080/health

# Access web interface
firefox http://localhost:8080
```

### **AI Assistant Features**

- 🔍 **Deployment troubleshooting**
- 📚 **Documentation and guidance**
- 🛠️ **Configuration assistance**
- 🚨 **Error analysis and solutions**

## 📚 Next Steps After Installation

### **1. Create Your First Virtual Machine**

```bash
# Source bash aliases
source ~/.bash_aliases

# List available commands
qubinode_help

# Create a VM (example)
kcli create vm test-vm
```

### **2. Access Management Tools**

```bash
# Cockpit web console
firefox https://localhost:9090

# Libvirt management
virt-manager  # If GUI available
virsh list --all  # Command line
```

### **3. Explore Documentation**

```bash
# View available documentation
ls docs/

# Read deployment guides
ls docs/deployments/

# Check ADRs (Architectural Decision Records)
ls docs/adrs/
```

## 🔐 Security Considerations

### **For Production Deployments**

1. **Change default passwords** in all configuration files
1. **Configure firewall rules** for your environment
1. **Set up proper DNS** with your domain
1. **Configure SSL certificates** for web interfaces
1. **Review user permissions** and access controls

### **For Development/Testing**

1. **Use isolated networks** to prevent conflicts
1. **Regular backups** of VM configurations
1. **Monitor resource usage** to prevent system overload

## 📞 Getting Help

### **Documentation**

- 📖 **Main README**: `/README.md`
- 🏗️ **Architecture Decisions**: `/docs/adrs/`
- 🚀 **Deployment Guides**: `/docs/deployments/`

### **AI Assistant**

- 🤖 **Web Interface**: `http://localhost:8080` (if enabled)
- 💬 **Chat Support**: Ask questions about deployment issues

### **Community**

- 🐛 **Issues**: GitHub Issues for bug reports
- 💡 **Discussions**: GitHub Discussions for questions
- 📧 **Contact**: Check repository for contact information

## ✅ Success Criteria

Your installation is successful when:

1. ✅ **Deploy script completes** without errors
1. ✅ **libvirtd service** is running
1. ✅ **DNS resolution** works properly
1. ✅ **Virtual networks** are configured
1. ✅ **Storage pools** are available
1. ✅ **Virtualization** validation passes
1. ✅ **Management tools** are accessible

______________________________________________________________________

**Last Updated**: November 2024
**Tested On**: RHEL 9/10, CentOS Stream 9/10, Rocky Linux 9, AlmaLinux 9
**Version**: Compatible with deploy-qubinode.sh v1.0.0+
