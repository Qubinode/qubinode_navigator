# Slim Airflow image for Qubinode Navigator
# ADR-0050: Hybrid Host-Container Architecture
# Heavy AI/ML components (sentence-transformers, litellm, aider) run on host
# This container focuses on orchestration only
#
# Based on official Apache Airflow 2.10.4
# Using Python 3.12 for forward compatibility (aligned with ADR-0001 and ADR-0025)
FROM docker.io/apache/airflow:2.10.4-python3.12

# Install uv for fast dependency management
USER root
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/uv && \
    mv /root/.local/bin/uvx /usr/local/bin/uvx || true
USER airflow

# Core dependencies for Qubinode integration
# These are lightweight and needed for DAG execution
RUN uv pip install --no-cache-dir \
    # HTTP client for calling host services
    httpx>=0.24.0 \
    # PostgreSQL vector extension client
    pgvector>=0.2.0 \
    psycopg2-binary>=2.9.0 \
    # Pydantic for data validation
    pydantic>=2.0.0

# ADR-0049 Phase 4: OpenLineage integration for data/code lineage
RUN uv pip install --no-cache-dir \
    apache-airflow-providers-openlineage>=1.0.0 \
    openlineage-python>=1.0.0

# ADR-0051: HashiCorp Vault integration for secrets management
# Official Airflow provider for Vault (includes VaultHook, VaultBackend)
RUN uv pip install --no-cache-dir \
    apache-airflow-providers-hashicorp>=3.0.0

# SSH provider for remote host execution (replaces manual SSH in BashOperator)
# Used for executing commands on host from container (kcli, virsh, ansible)
RUN uv pip install --no-cache-dir \
    apache-airflow-providers-ssh>=3.0.0

# ADR-0038: FastMCP framework for MCP server
# Required for MCP server integration with Claude/AI assistants
RUN uv pip install --no-cache-dir \
    fastmcp>=0.1.0 \
    mcp>=1.0.0 \
    starlette>=0.27.0 \
    uvicorn>=0.23.0 \
    sse-starlette>=1.6.0

# ============================================================================
# REMOVED FROM CONTAINER (now run on host per ADR-0050):
# ============================================================================
# - sentence-transformers (1.5GB with PyTorch) -> Host embedding service :8891
# - litellm (500MB+) -> Host LiteLLM proxy :4000
# - aider-chat -> Host tool, direct filesystem access
# - kcli, libvirt-python -> Host tool, direct libvirt access
# - libvirt-dev, gcc, python3-dev -> Not needed without libvirt-python
# ============================================================================

# Environment variables for host service integration
ENV QUBINODE_EMBEDDING_SERVICE_URL=http://localhost:8891 \
    QUBINODE_LITELLM_PROXY_URL=http://localhost:4000 \
    QUBINODE_OLLAMA_URL=http://localhost:11434

# Stay as airflow user
USER airflow
