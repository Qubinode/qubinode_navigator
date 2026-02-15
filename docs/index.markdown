______________________________________________________________________

## layout: default title: Qubinode Navigator nav_order: 1 description: "Modern AI-enhanced infrastructure automation platform with plugin architecture" permalink: /

# Qubinode Navigator

{: .fs-9 }

Modern AI-enhanced, container-first infrastructure automation platform with modular plugin architecture, supporting RHEL 10, CentOS Stream 10, and next-generation enterprise deployments.
{: .fs-6 .fw-300 }

[Get started now](#getting-started){: .btn .btn-primary .fs-5 .mb-4 .mb-md-0 .mr-2 }
[View on GitHub](https://github.com/Qubinode/qubinode_navigator){: .btn .fs-5 .mb-4 .mb-md-0 }

______________________________________________________________________

## Overview

Qubinode Navigator is a next-generation infrastructure automation platform built with a **modular plugin architecture** and **AI-enhanced capabilities**. It simplifies enterprise infrastructure deployment across multiple operating systems and cloud providers, with special focus on **RHEL 10/CentOS Stream 10** support and **container-first execution**.

## 🚀 Key Features

- **🔌 Plugin Architecture**: Extensible framework with OS, cloud provider, and deployment plugins
- **🤖 AI-Powered Assistant**: PydanticAI orchestrator with RAG-powered documentation search and intent-based deployment
- **🖥️ Next-Gen OS Support**: Native RHEL 10, CentOS Stream 10, Rocky Linux, and Fedora support
- **📦 Container-First**: Ansible Navigator execution with standardized environments
- **🌐 Multi-Cloud Ready**: Equinix, Hetzner, AWS, and bare-metal deployments
- **🔒 Enterprise Security**: HashiCorp Vault integration and progressive SSH security
- **📊 Workflow Orchestration**: Apache Airflow DAGs for automated VM provisioning, service deployment, and infrastructure health checks
- **🧪 Comprehensive Testing**: 84%+ test coverage with real deployment validation

______________________________________________________________________

## Quick Start

### Prerequisites

- **Operating System**: RHEL 9/10, CentOS Stream 10, Rocky Linux 9+, or Fedora 39+ (RHEL 8: legacy/compatibility only)
- **Memory**: Minimum 4GB RAM (8GB+ recommended for AI features)
- **Storage**: 500GB+ available space
- **Container Runtime**: Podman or Docker
- **Network**: Internet connectivity for package downloads

### Modern Installation (Recommended)

```bash
# Clone the repository
git clone https://github.com/Qubinode/qubinode_navigator.git
cd qubinode_navigator

# Run the modernized setup script with plugin framework
./scripts/development/setup_modernized.sh
```

### Plugin Framework CLI

```bash
# List available plugins
python3 qubinode_cli.py list

# Deploy with specific OS plugin
python3 qubinode_cli.py deploy --plugin rhel10

# Get plugin information
python3 qubinode_cli.py info --plugin centos_stream10
```

### Legacy Installation

```bash
# Traditional setup script (compatibility mode)
./scripts/development/setup.sh
```

______________________________________________________________________

## Deployment Options

| Deployment Method          | Description                                                                                                                            |
| :------------------------- | :------------------------------------------------------------------------------------------------------------------------------------- |
| **Automated with Airflow** | Use Apache Airflow for orchestrated, reproducible deployments - see [Airflow Getting Started](/tutorials/airflow-getting-started.html) |
| **Production Deployment**  | Follow best practices for production environments - see [Deploy to Production](/how-to/deploy-to-production.html)                      |
| **MCP Integration**        | Deploy with Model Context Protocol servers - see [MCP Production Setup](/tutorials/mcp-production-and-client.html)                     |

______________________________________________________________________

## 🏗️ Architecture & Design

Qubinode Navigator follows a **modern, plugin-based architecture** with comprehensive decision documentation:

### 📋 **Latest Architectural Decisions (2025)**

- [**ADR-0026**: RHEL 10/CentOS 10 Platform Support Strategy](https://github.com/Qubinode/qubinode_navigator/blob/main/docs/adrs/adr-0026-rhel-10-centos-10-platform-support-strategy.md)
- [**ADR-0027**: CPU-Based AI Deployment Assistant Architecture](https://github.com/Qubinode/qubinode_navigator/blob/main/docs/adrs/adr-0027-cpu-based-ai-deployment-assistant-architecture.md)
- [**ADR-0028**: Modular Plugin Framework for Extensibility](https://github.com/Qubinode/qubinode_navigator/blob/main/docs/adrs/adr-0028-modular-plugin-framework-for-extensibility.md)
- [**ADR-0029**: Documentation Strategy and Website Modernization](https://github.com/Qubinode/qubinode_navigator/blob/main/docs/adrs/adr-0029-documentation-strategy-and-website-modernization.md)
- [**ADR-0030**: Software and OS Update Strategy](https://github.com/Qubinode/qubinode_navigator/blob/main/docs/adrs/adr-0030-software-and-os-update-strategy.md)

### 🏛️ **Foundation ADRs**

- [**ADR-0001**: Container-First Execution Model](https://github.com/Qubinode/qubinode_navigator/blob/main/docs/adrs/adr-0001-container-first-execution-model-with-ansible-navigator.md)
- [**ADR-0004**: Security Architecture with Ansible Vault](https://github.com/Qubinode/qubinode_navigator/blob/main/docs/adrs/adr-0004-security-architecture-ansible-vault.md)
- [**ADR-0023**: HashiCorp Vault Integration](https://github.com/Qubinode/qubinode_navigator/blob/main/docs/adrs/adr-0023-enhanced-configuration-management-with-template-support-and-hashicorp-vault-integration.md)

### 🔐 **Enterprise Security**

- **HashiCorp Vault Integration**: Centralized secret management
- **Ansible Vault**: Encrypted configuration files and credentials
- **Progressive SSH Security**: Multi-layered access controls and key management
- **Container Isolation**: Secure execution environments with Ansible Navigator
- **Credential Scanning**: Automated detection of exposed secrets

### 🔌 **Plugin Architecture**

- **OS Plugins**: RHEL 9/10, CentOS Stream 10, Rocky Linux 9+, Fedora (RHEL 8: legacy only)
- **Cloud Plugins**: Equinix, Hetzner, AWS integrations
- **Environment Plugins**: Red Hat Demo, development, production configurations
- **Service Plugins**: Vault integration, monitoring, logging
- **Extensible Framework**: Easy plugin development with standardized interfaces

______________________________________________________________________

## Documentation Sections

This site follows the [Diataxis](https://diataxis.fr/) framework for clear, well-organized documentation:

| Section                                                                        | Description                                                           |
| :----------------------------------------------------------------------------- | :-------------------------------------------------------------------- |
| [**Tutorials**](/tutorials/)                                                   | Learning-oriented guides that take you through a process step by step |
| [**How-To Guides**](/how-to/)                                                  | Task-oriented recipes for accomplishing specific goals                |
| [**Reference**](/reference/)                                                   | Information-oriented technical descriptions and API documentation     |
| [**Explanation**](/explanation/)                                               | Understanding-oriented discussions that clarify concepts              |
| [**ADRs**](https://github.com/Qubinode/qubinode_navigator/tree/main/docs/adrs) | Architecture Decision Records documenting key design choices          |

______________________________________________________________________

## Community & Support

### 🤝 Contributing

We welcome contributions from the community! Here's how you can get involved:

- **📝 Documentation**: Help improve our guides and documentation
- **🐛 Bug Reports**: Report issues and help us improve
- **💡 Feature Requests**: Suggest new features and enhancements
- **🔧 Code Contributions**: Submit pull requests with improvements

Read our [Contributing Guide](/how-to/contribute.html) to get started.

### 📞 Support

- **GitHub Issues**: [Report bugs and request features](https://github.com/Qubinode/qubinode_navigator/issues)
- **Documentation**: Comprehensive guides and troubleshooting
- **Community**: Join discussions and share experiences

______________________________________________________________________

## License

This project is licensed under the [GNU General Public License v3.0](https://github.com/Qubinode/qubinode_navigator/blob/main/LICENSE).

______________________________________________________________________

*Qubinode Navigator - Simplifying OpenShift deployment on KVM infrastructure.*
