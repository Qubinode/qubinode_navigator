# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Qubinode Navigator is an AI-enhanced, container-first infrastructure automation platform for deploying OpenShift clusters, VMs, and supporting services on KVM hypervisors. It combines:

- **Airflow** for workflow orchestration (DAGs)
- **AI Assistant** with PydanticAI orchestrator for intent-based deployment
- **MCP Servers** for LLM tool integration
- **Plugin architecture** for extensible deployments

## Build Commands

```bash
# Full stack deployment (recommended)
sudo -E ./scripts/development/deploy-qubinode.sh

# Airflow installation (from airflow/ directory)
cd airflow && make install    # Full: prereqs + build + start
cd airflow && make uninstall  # Stop and remove containers/volumes

# Build execution environment container
make build-image

# Install ansible-navigator
make install-ansible-navigator

# Run tests
python3 -m pytest tests/unit/
python3 -m pytest tests/integration/
python3 -m pytest tests/unit/test_rhel10_plugin.py -v

# MCP server tests
make test-mcp           # Full suite
make test-mcp-airflow   # Airflow MCP only
make test-mcp-ai        # AI Assistant MCP only
```

## Architecture

### Core Framework (`core/`)

- `plugin_manager.py` - Plugin discovery and dependency resolution
- `config_manager.py` - Configuration loading from `config/plugins.yml`
- `base_plugin.py` - Base class for all plugins (ADR-0028 compliant)
- `event_system.py` - Event bus for inter-plugin communication

### Plugin System (`plugins/`)

Plugins implement `QubiNodePlugin` base class with methods:

- `_initialize_plugin()`, `check_state()`, `get_desired_state()`, `apply_changes()`

Families:

- `plugins/os/` - RHEL 9/10, Rocky Linux 9+, CentOS Stream 9/10 (RHEL 8: legacy only)
- `plugins/cloud/` - Hetzner, Equinix
- `plugins/services/` - AI Assistant, Vault, Log Analysis
- `plugins/environments/` - Deployment contexts

### Airflow Layer (`airflow/`)

- `dags/` - Workflow DAG definitions
- `plugins/qubinode/` - Custom operators (KcliVMCreate/Delete/List)
- `scripts/mcp_server_fastmcp.py` - Primary MCP server (20+ tools)

### AI Assistant (`ai-assistant/`)

- FastAPI service with PydanticAI orchestrator (ADR-0063, ADR-0066)
- Three-agent system: Manager, Developer, Observer
- RAG-powered documentation search

## Services and Ports

| Service      | Port | Purpose                       |
| ------------ | ---- | ----------------------------- |
| AI Assistant | 8080 | PydanticAI orchestrator + RAG |
| Airflow UI   | 8888 | DAG management                |
| MCP Server   | 8889 | Tool API for LLM integration  |
| PostgreSQL   | 5432 | Metadata + pgvector           |
| Marquez API  | 5001 | Lineage tracking              |
| Marquez Web  | 3000 | Lineage visualization         |

## DAG Development Standards (ADR-0045)

**Critical rules:**

1. Use `"""` (triple double quotes) for `bash_command`, NEVER `'''`
1. DAG IDs must be snake_case matching filename
1. ASCII-only log prefixes: `[OK]`, `[ERROR]`, `[WARN]`, `[INFO]`, `[SKIP]`
1. No string concatenation in `bash_command`
1. No Unicode/emoji in bash commands
1. **Always use `get_kcli_prefix()` for kcli commands** (see below)

**kcli commands - IMPORTANT:**

kcli requires root/sudo privileges for VM operations. Use the helper from `dag_helpers.py`:

```python
from dag_helpers import get_ssh_conn_id, get_kcli_prefix

# Get prefix once at module level (evaluated at DAG parse time)
KCLI = get_kcli_prefix()  # Returns "sudo " or "" based on environment

# Use in SSHOperator commands (f-string required)
create_vm = SSHOperator(
    task_id="create_vm",
    ssh_conn_id=get_ssh_conn_id(),
    command=f"""
    {KCLI}kcli list vm
    {KCLI}kcli create vm myvm -i centos9stream
    {KCLI}kcli info vm myvm
    """,
    dag=dag,
)
```

The prefix is controlled by:

- `QUBINODE_KCLI_SUDO=true|false` - Explicit control
- Auto-detect: Uses sudo if `QUBINODE_SSH_USER` is not root

**SSH execution pattern (ADR-0046):**

```python
bash_command="""
ssh -o StrictHostKeyChecking=no root@localhost \
    "cd /opt/kcli-pipelines && ./deploy.sh"
"""
```

**F-string + Jinja2 + Shell Escaping Rules (CRITICAL):**

DAG commands pass through THREE interpreters. Memorize these rules:

| Goal                     | In f-string          | After f-string   | After Jinja2 |
| ------------------------ | -------------------- | ---------------- | ------------ |
| Literal `{` for awk      | `{{`                 | `{`              | `{`          |
| Jinja2 param             | `{{{{ params.x }}}}` | `{{ params.x }}` | value        |
| Shell `$VAR`             | `$VAR`               | `$VAR`           | `$VAR`       |
| Shell `${VAR}`           | `${{VAR}}`           | `${VAR}`         | `${VAR}`     |
| awk `$2` (double-quoted) | `\\$2`               | `\$2`            | `$2`         |

**Common mistakes:**

```python
# WRONG: Quadruple braces for awk - Jinja2 interprets as template
awk "{{{{print \\$2}}}}"  # -> awk "{{print \$2}}" -> Jinja2 ERROR!

# CORRECT: Double braces for awk - passes through Jinja2 unchanged
awk "{{print \\$2}}"      # -> awk "{print \$2}" -> awk "{print $2}"

# CORRECT: Quadruple braces for Jinja2 params
DOMAIN="{{{{ params.domain }}}}"  # -> DOMAIN="{{ params.domain }}" -> DOMAIN="example.com"
```

**Use helper snippets from `dag_helpers.py`:**

```python
from dag_helpers import get_vm_ip_snippet, get_awk_field_snippet

# Instead of writing complex escaping manually:
command = f'''
VM_NAME="freeipa"
{get_vm_ip_snippet()}  # Handles escaping correctly
echo "IP: $IP"
'''
```

**Validate before committing:**

```bash
# Syntax check
python3 -c "import ast; ast.parse(open('airflow/dags/my_dag.py').read())"

# Import check
python3 -c "from airflow.models import DagBag; db = DagBag('airflow/dags'); print(db.import_errors)"

# Lint for ADR compliance
cd airflow && make lint-dags
```

## Code Style

**Python:**

- PEP 8 compliant
- Type hints required
- f-strings preferred

**Bash:**

- shellcheck compliant
- Use `[[` over `[` for conditionals
- Use `set -euo pipefail` for scripts

## Key Commands

```bash
# CLI entry point
python3 qubinode_cli.py list                    # List plugins
python3 qubinode_cli.py execute --plugins RHEL10Plugin
python3 qubinode_cli.py ask "question"          # Query AI Assistant

# Airflow DAG management (from airflow/)
make list-dags
make validate-dags
make clear-dag-cache
make clear-dag-cache-id DAG_ID=freeipa_deployment

# VM operations (requires sudo)
sudo kcli list vm
sudo kcli info vm <name>

# Service status
sudo podman ps
curl http://localhost:8080/orchestrator/status
curl http://localhost:8888/health

# Agentic Workflows (gh-aw)
gh aw list                       # List all agentic workflows
gh aw run doc-noob-tester        # Validate docs for accuracy and consistency
gh aw run daily-qa               # Run weekly QA health check on demand
# ci-doctor triggers automatically on CI failure (no manual run needed)
gh aw compile                    # Recompile after editing .md workflow files
gh aw logs <workflow-name>       # View logs from a workflow run
gh aw status                     # Check workflow status
```

## Container Runtime

Podman is the primary runtime (RHEL-based systems). Scripts assume Podman paths and commands.

## Important ADRs

| ADR      | Topic                                |
| -------- | ------------------------------------ |
| ADR-0001 | Container-first execution model      |
| ADR-0028 | Plugin architecture                  |
| ADR-0036 | Airflow integration architecture     |
| ADR-0045 | DAG development standards (CRITICAL) |
| ADR-0046 | Validation pipeline & host execution |
| ADR-0063 | PydanticAI core orchestrator         |
| ADR-0066 | Developer Agent DAG validation       |

## Sensitive Files (Never Commit)

- `.env` - Credentials
- `config/vault.yml` - Vault tokens
- `*.pem`, `*.key` - Certificates
- `pull-secret.json` - OpenShift pull secrets

## Commit Convention

```
feat|fix|docs|refactor|test|chore(scope): message

# Reference ADRs when applicable
feat(dag): Add keycloak deployment DAG (ADR-0047)
```
