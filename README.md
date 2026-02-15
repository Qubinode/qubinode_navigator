# Qubinode Navigator

**Modern Enterprise Infrastructure Automation Platform**
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/Qubinode/qubinode_navigator)

Qubinode Navigator is an AI-enhanced, container-first infrastructure automation platform that provides hypervisor deployment and management capabilities across multiple cloud providers and operating systems. Built with a modular plugin architecture, it supports the latest enterprise Linux distributions including RHEL 10 and CentOS Stream 10.

## TL;DR

**Qubinode Navigator** - Modern Enterprise Infrastructure Automation Platform with AI-powered MCP servers.

**Key features:**

- **🔌 Modular Plugin Architecture**: Extensible framework with OS, cloud provider, and deployment plugins
- **🤖 AI-Powered MCP Servers**: Model Context Protocol integration for LLM-driven infrastructure management
- **Airflow MCP Server**: DAG management and VM operations (9 tools)
- **AI Assistant MCP Server**: RAG-powered documentation search and chat (3 tools)

**Quick start:** `git clone https://github.com/Qubinode/qubinode_navigator.git && cd qubinode_navigator && ./deploy-qubinode-with-airflow.sh`

## 🚀 Key Features

- **🔌 Modular Plugin Architecture**: Extensible framework with OS, cloud provider, and deployment plugins
- **🤖 AI-Powered MCP Servers**: Model Context Protocol integration for LLM-driven infrastructure management
  - **Airflow MCP Server**: DAG management and VM operations (9 tools)
  - **AI Assistant MCP Server**: RAG-powered documentation search and chat (3 tools)
- **📦 Container-First Execution**: All deployments use Ansible Navigator with standardized execution environments
- **🌐 Multi-Cloud Support**: Equinix, Hetzner, AWS, and bare-metal deployments
- **🔒 Enterprise Security**: Ansible Vault integration with HashiCorp Vault support
- **📊 Automated Updates**: Intelligent update detection and compatibility validation (planned)

## 🖥️ Supported Platforms

- **RHEL 9/10** - Full enterprise support with subscription management
- **CentOS Stream 9/10** - Next-generation enterprise Linux
- **Rocky Linux 9+** - RHEL-compatible community distribution
- **Fedora 39+** - Cutting-edge features and packages

**Note**: RHEL 8 is legacy and not recommended for new deployments. See [ADR-0026](docs/adrs/adr-0026-rhel-10-centos-10-platform-support-strategy.md) for platform support details.

## 📋 Prerequisites

- Linux-based operating system (RHEL 9+, CentOS Stream 9+, Rocky Linux 9+, or Fedora 39+)
- Git
- Podman or Docker
- **8GB+ RAM** (16GB+ recommended for AI features)
- **50GB+ disk space** (100GB+ recommended)
- Hardware virtualization enabled (VT-x/AMD-V)
- **Network**: Internet access for container images and packages
- **Repositories**: kcli-pipelines and openshift-agent-install (cloned automatically by deploy scripts)

## 🚀 Quick Start

### Choose Your Deployment Method

Qubinode Navigator offers three deployment scripts for different use cases:

| Method                       | Script                                             | Best For                       | Features                                              |
| ---------------------------- | -------------------------------------------------- | ------------------------------ | ----------------------------------------------------- |
| **Full Stack** (Recommended) | `./deploy-qubinode-with-airflow.sh`                | New users, complete platform   | Airflow + AI Assistant + PostgreSQL + Marquez + Nginx |
| **Development**              | `sudo -E ./scripts/development/deploy-qubinode.sh` | Contributors, testing features | Latest development features, debugging tools          |
| **Basic**                    | `./deploy-qubinode.sh`                             | Advanced users, minimal setup  | Core components only (symlink to development script)  |

> **Note**: `deploy-qubinode.sh` is a symbolic link to `scripts/development/deploy-qubinode.sh`. For the most comprehensive setup including Airflow orchestration, use `deploy-qubinode-with-airflow.sh`.

### Modern Setup (Recommended)

```bash
# Clone the repository
git clone https://github.com/Qubinode/qubinode_navigator.git
cd qubinode_navigator

# Run pre-flight checks
./scripts/preflight-check.sh --fix

# Deploy full stack (recommended for most users)
./deploy-qubinode-with-airflow.sh

# OR: Deploy development version
# sudo -E ./scripts/development/deploy-qubinode.sh
```

### Running as Non-Root User

For security best practices, you can run as a dedicated `lab-user` instead of root:

```bash
# Create lab-user with sudo privileges
curl -OL https://gist.githubusercontent.com/tosin2013/385054f345ff7129df6167631156fa2a/raw/b67866c8d0ec220c393ea83d2c7056f33c472e65/configure-sudo-user.sh
chmod +x configure-sudo-user.sh
./configure-sudo-user.sh lab-user

# Switch to lab-user and configure SSH
sudo su - lab-user
ssh-keygen -f ~/.ssh/id_rsa -t rsa -N ''
IP_ADDRESS=$(hostname -I | awk '{print $1}')
ssh-copy-id lab-user@${IP_ADDRESS}
```

See the **[Getting Started Guide](docs/GETTING_STARTED.md#running-as-non-root-user-recommended)** for complete non-root setup instructions.

### Legacy Setup

```bash
curl https://raw.githubusercontent.com/Qubinode/qubinode_navigator/main/setup.sh | bash
```

### Services After Deployment

| Deployment Mode | Airflow UI              | AI Assistant               | MCP Server |
| --------------- | ----------------------- | -------------------------- | ---------- |
| **Full Stack**  | http://YOUR_IP/ (Nginx) | http://YOUR_IP/ai/ (Nginx) | :8889      |
| **Development** | http://YOUR_IP:8888     | http://YOUR_IP:8080        | :8889      |

> **Note**: The full stack deployment (`deploy-qubinode-with-airflow.sh`) includes an Nginx reverse proxy on port 80. Development deployments expose services on their direct ports.

### Plugin Framework CLI

```bash
# List available plugins
python3 qubinode_cli.py list

# Deploy with specific OS plugin
python3 qubinode_cli.py deploy --plugin rhel10

# Get plugin information
python3 qubinode_cli.py info --plugin rocky_linux
```

## 🏗️ Architecture

Qubinode Navigator follows a **container-first, plugin-based architecture**:

- **Core Framework** (`core/`): Plugin manager, configuration, and event system
- **OS Plugins** (`plugins/os/`): Operating system-specific deployment logic
- **Cloud Plugins** (`plugins/cloud/`): Cloud provider integrations
- **Environment Plugins** (`plugins/environments/`): Deployment environment configurations

## 📚 Documentation

- **[Complete Documentation](https://qubinode.github.io/qubinode_navigator/)** - Full documentation website
- **[Getting Started Guide](docs/GETTING_STARTED.md)** - Quick start with AI orchestrator and non-root setup
- **[MCP Quick Start](MCP-QUICK-START.md)** - Get started with MCP servers in 5 minutes
- **[MCP Server Guide](MCP-SERVER-GUIDE.md)** - Complete MCP server setup and FastMCP implementation
- **[Installation Guide](docs/tutorials/getting-started.md)** - Step-by-step installation instructions
- **[User Guide](docs/how-to/)** - Practical how-to guides
- **[API Reference](docs/reference/)** - Complete API documentation
- **[Architecture Overview](docs/explanation/architecture-overview.md)** - Technical architecture details
- **[Architecture Decision Records](docs/adrs/)** - Design decisions and rationale
- **[Developer Guide](https://qubinode.github.io/qubinode_navigator/development/developers_guide.html)** - Contributing guidelines

## 🧪 Testing

The project includes comprehensive testing:

```bash
# Run unit tests
python3 -m pytest tests/unit/

# Run integration tests
python3 -m pytest tests/integration/

# Test specific plugin
python3 -m pytest tests/unit/test_rhel10_plugin.py -v
```

## 🤝 Contributing

We welcome contributions! Please see our [Developer's Guide](https://qubinode.github.io/qubinode_navigator/development/developers_guide.html) for:

- Development setup
- Plugin development guidelines
- Testing requirements
- Code style standards

## 📄 License

This project is licensed under the terms specified in the [LICENSE](LICENSE) file.

## 🔗 Related Projects

- [qubinode_kvmhost_setup_collection](qubinode_kvmhost_setup_collection/) - Ansible collection for KVM host setup
- [Ansible Navigator](https://ansible-navigator.readthedocs.io/) - Container-based Ansible execution
