---
title: Architecture Overview
parent: Explanation
nav_order: 1
---

# Architecture Overview

This document explains the architectural concepts and design philosophy behind Qubinode Navigator's modern, container-first infrastructure automation platform.

## Introduction

Qubinode Navigator is built around three core architectural principles:

1. **Container-First Execution** - All automation runs in standardized container environments
1. **Modular Plugin Framework** - Extensible architecture supporting multiple platforms and clouds
1. **AI-Enhanced Operations** - Intelligent assistance for deployment and troubleshooting

Understanding these principles helps explain why the system is structured the way it is and how different components work together.

## Core Concepts

### Container-First Execution Model

Qubinode Navigator uses **Ansible Navigator** to execute all automation inside containers rather than directly on the host system. This approach solves the "works on my machine" problem by ensuring:

- **Consistent environments** across all deployment targets
- **Isolated dependencies** - each execution has its own Python version, Ansible collections, and system libraries
- **Reproducible builds** - the same container image produces identical results
- **No host pollution** - no installation of conflicting packages on the host

The trade-off is slightly longer startup times for containerized execution, but the consistency benefits far outweigh this minor cost.

See [ADR-0001: Container-First Execution Model](https://github.com/Qubinode/qubinode_navigator/blob/main/docs/adrs/adr-0001-container-first-execution-model-with-ansible-navigator.md) for the full decision rationale.

### Modular Plugin Framework

The plugin architecture allows Qubinode Navigator to support multiple:

- **Operating systems** (RHEL 8/9/10, CentOS Stream, Rocky Linux, Fedora)
- **Cloud providers** (Equinix Metal, Hetzner, AWS, bare metal)
- **Deployment scenarios** (development, staging, production)

Each plugin is self-contained with its own:

- Configuration templates
- Validation rules
- Deployment workflows
- Environment-specific settings

This modularity means adding support for a new OS or cloud provider requires only creating a new plugin, not modifying core code.

See [ADR-0028: Modular Plugin Framework](https://github.com/Qubinode/qubinode_navigator/blob/main/docs/adrs/adr-0028-modular-plugin-framework-for-extensibility.md) for implementation details.

### Progressive Security Model

Security in Qubinode Navigator follows a layered approach:

1. **Credential encryption** - Ansible Vault for at-rest encryption
1. **Secret management** - Optional HashiCorp Vault integration for centralized secrets
1. **SSH hardening** - Progressive key-based authentication with role-based access
1. **Container isolation** - Execution environments prevent lateral movement

This progressive model allows starting with basic security (Ansible Vault) and adding layers (HashiCorp Vault, advanced SSH) as needs evolve.

See [ADR-0004: Security Architecture](https://github.com/Qubinode/qubinode_navigator/blob/main/docs/adrs/adr-0004-security-architecture-ansible-vault.md) for details.

## Design Decisions

### Why Container-First?

**Traditional approach problems:**

- Different Python versions across systems
- Missing or conflicting Ansible collections
- Varied system library versions
- Manual dependency management

**Container-first benefits:**

- Single source of truth (container image)
- Automated dependency management
- Tested, versioned environments
- Trivial rollback (use previous image)

The cost is requiring Podman/Docker, but this is standard infrastructure today.

### Why Plugin Architecture?

**Monolithic approach problems:**

- OS-specific logic scattered through codebase
- Difficult to test individual platforms
- Cloud provider changes require core modifications
- New platform support is high-risk

**Plugin approach benefits:**

- Clear separation of concerns
- Independent plugin testing
- New platforms don't affect existing ones
- Community contributions easier

The cost is slightly more complex project structure, but this pays dividends at scale.

### Why Apache Airflow Integration?

**Script-based deployment problems:**

- No workflow visibility
- Difficult to restart failed steps
- No scheduling or orchestration
- Manual tracking of deployments

**Airflow benefits:**

- Visual DAG representation
- Automatic retry logic
- Scheduling and triggers
- Deployment history and logs
- Extensible with custom operators

The cost is additional infrastructure (Airflow + database), but this is optional—scripts still work standalone.

See [ADR-0036: Airflow Integration](https://github.com/Qubinode/qubinode_navigator/blob/main/docs/adrs/adr-0036-apache-airflow-workflow-orchestration-integration.md) for the full analysis.

## Comparison with Alternatives

### Infrastructure Automation Approaches

| Approach                           | Pros                                     | Cons                                       | Best For                                       |
| ---------------------------------- | ---------------------------------------- | ------------------------------------------ | ---------------------------------------------- |
| **Container-First (Our Approach)** | Reproducible, isolated, consistent       | Container overhead, requires Podman/Docker | Multi-platform, multi-cloud deployments        |
| **Direct Ansible Execution**       | Simple, fast startup, no containers      | Environment drift, dependency conflicts    | Single-platform, controlled environments       |
| **Terraform + Ansible**            | Infrastructure as code, state management | Complex toolchain, learning curve          | Cloud-native, stateful infrastructure          |
| **Chef/Puppet**                    | Mature, enterprise support, agent-based  | Heavy agent, older paradigms               | Large fleets, ongoing configuration management |

### Secret Management Approaches

| Approach                       | Pros                                  | Cons                                   | Best For                                   |
| ------------------------------ | ------------------------------------- | -------------------------------------- | ------------------------------------------ |
| **Ansible Vault (Default)**    | Built-in, simple, file-based          | Manual key distribution, no audit logs | Small teams, simple deployments            |
| **HashiCorp Vault (Optional)** | Centralized, audited, dynamic secrets | Additional infrastructure, complexity  | Enterprise, compliance-driven environments |
| **Cloud KMS**                  | Cloud-native, managed service         | Vendor lock-in, cost                   | Cloud-only deployments                     |

## Further Reading

### Tutorials

- [Getting Started](../tutorials/getting-started.md) - Basic deployment walkthrough
- [Airflow Integration](../tutorials/airflow-getting-started.md) - Orchestrated deployments

### How-To Guides

- [Deploy to Production](../how-to/deploy-to-production.md) - Production best practices

### Architecture Decision Records

- [ADR-0001: Container-First Execution](https://github.com/Qubinode/qubinode_navigator/blob/main/docs/adrs/adr-0001-container-first-execution-model-with-ansible-navigator.md)
- [ADR-0028: Modular Plugin Framework](https://github.com/Qubinode/qubinode_navigator/blob/main/docs/adrs/adr-0028-modular-plugin-framework-for-extensibility.md)
- [ADR-0036: Airflow Integration](https://github.com/Qubinode/qubinode_navigator/blob/main/docs/adrs/adr-0036-apache-airflow-workflow-orchestration-integration.md)
- [Browse all ADRs](https://github.com/Qubinode/qubinode_navigator/tree/main/docs/adrs) for complete architectural decisions
