---
title: AI Assistant Interaction Guide
parent: Guides
nav_order: 3
---

# AI Assistant Interaction Guide

## Overview

The Qubinode Navigator includes an integrated AI Assistant that provides intelligent troubleshooting and guidance throughout your deployment journey. The AI Assistant is **automatically integrated** - no manual commands required!

## How It Works

### During Deployment

The AI Assistant automatically activates when you run the deployment script:

```bash
./deploy-qubinode.sh
```

**If any errors occur**, you'll see automatic AI assistance:

```
[ERROR] Failed to install RHEL 10 packages
[AI ASSISTANT] Analyzing error and providing troubleshooting guidance...
╔══════════════════════════════════════════════════════════════╗
║                    AI ASSISTANT GUIDANCE                     ║
╚══════════════════════════════════════════════════════════════╝
The package installation failure on RHEL 10 is likely due to:

1. Repository connectivity issues
   - Check: ping 8.8.8.8
   - Verify: dnf repolist

2. Insufficient system resources
   - Check: free -h (need 8GB+ RAM)
   - Check: df -h (need 50GB+ disk)

3. Missing RHEL subscription
   - Run: subscription-manager status
   - Register if needed: subscription-manager register

Try running the deployment again after addressing these issues.

For more help, visit: http://localhost:8080
```

### After Deployment

Once deployment completes successfully, the AI Assistant remains available to help you build on your infrastructure:

```
╔══════════════════════════════════════════════════════════════╗
║                   DEPLOYMENT COMPLETED                       ║
╚══════════════════════════════════════════════════════════════╝

AI Assistant Available:
  • URL: http://localhost:8080
  • Ask for help with: deployment issues, troubleshooting, best practices

Next Steps:
  1. Review deployment log: /tmp/qubinode-deployment-20251111-050000.log
  2. Check running VMs: virsh list --all
  3. Access Qubinode Navigator: /opt/qubinode-navigator
  4. Ask AI Assistant for guidance on next steps
```

## Post-Deployment Interactions

### Option 1: Web Interface (Recommended)

Simply open your browser and visit: **http://localhost:8080**

You can ask questions like:

- "How do I deploy OpenShift on this KVM infrastructure?"
- "What monitoring solutions work well with this setup?"
- "How do I add more virtual machines?"
- "Show me how to configure networking for my VMs"

### Option 2: Simple Command Line

For natural terminal interactions, just use the `qubinode` command:

```bash
# Ask for OpenShift deployment guidance
./qubinode "How do I deploy OpenShift 4.14 on my KVM infrastructure?"

# Get monitoring recommendations
./qubinode "What monitoring solutions work well with this setup?"

# Ask about VM management
./qubinode "How do I create and manage additional VMs?"

# Ask about networking
./qubinode "How do I configure networking for my VMs?"

# Get troubleshooting help
./qubinode "My VM won't start, what should I check?"
```

**That's it!** No curl commands, no JSON formatting - just ask your question naturally.

## Common Use Cases

### 1. Troubleshooting Deployment Issues

**No action needed** - AI automatically provides guidance when errors occur during `./deploy-qubinode.sh`

### 2. Learning Next Steps

After successful deployment, ask the AI:

```bash
./qubinode "What can I do with this infrastructure?"
./qubinode "Show me some example workloads I can deploy"
./qubinode "How do I get started with container orchestration?"
```

### 3. Extending Your Infrastructure

Get guidance on building more services:

```bash
./qubinode "How do I deploy OpenShift on this KVM infrastructure?"
./qubinode "How do I create additional VMs for development workloads?"
./qubinode "How do I configure advanced networking for my VMs?"
./qubinode "How do I add persistent storage to my setup?"
./qubinode "How do I set up monitoring and alerting?"
```

### 4. Best Practices and Optimization

Ask for expert advice:

```bash
./qubinode "How do I optimize performance for my workload?"
./qubinode "What security hardening should I apply?"
./qubinode "How do I backup and restore my VMs?"
./qubinode "What are the resource requirements for different workloads?"
```

## AI Assistant Capabilities

The AI Assistant has knowledge about:

- ✅ **Qubinode Navigator architecture and components**
- ✅ **KVM/libvirt virtualization management**
- ✅ **OpenShift and Kubernetes deployment**
- ✅ **RHEL/CentOS/Rocky Linux administration**
- ✅ **Ansible automation and playbooks**
- ✅ **Container technologies (Podman/Docker)**
- ✅ **Networking and storage configuration**
- ✅ **Troubleshooting common deployment issues**

## Health Check

To verify the AI Assistant is running:

```bash
curl -s http://localhost:8080/health
```

Expected response:

```json
{"status": "healthy", "model": "loaded", "timestamp": "2025-11-11T05:00:00Z"}
```

## Troubleshooting AI Assistant

If the AI Assistant isn't responding:

1. **Check if container is running**:

   ```bash
   podman ps | grep qubinode-ai-assistant
   ```

1. **Check container logs**:

   ```bash
   podman logs qubinode-ai-assistant
   ```

1. **Restart AI Assistant**:

   ```bash
   podman restart qubinode-ai-assistant
   ```

1. **Verify port accessibility**:

   ```bash
   curl -s http://localhost:8080/health
   ```

## Future Enhancements

The AI Assistant architecture is designed to support:

- 🔄 **Hugging Face integration** for advanced AI models
- 🔄 **Community showcase** capabilities
- 🔄 **Enhanced model training** on deployment patterns
- 🔄 **Multi-language support** for international users

## Getting Help

If you need additional assistance:

1. **Check the AI Assistant first**: http://localhost:8080
1. **Review deployment logs**: Check the log file path shown at deployment completion
1. **Consult documentation**: Browse `/docs/` directory in the repository
1. **Community support**: Visit the project repository for issues and discussions

______________________________________________________________________

**Remember**: The AI Assistant is your intelligent companion throughout the entire Qubinode Navigator journey - from initial deployment through advanced infrastructure management!
