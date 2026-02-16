______________________________________________________________________

## layout: default title: ADR-0036 Airflow Workflow Orchestration parent: Architecture & Design grand_parent: Architectural Decision Records nav_order: 36

# ADR-0036: Apache Airflow Workflow Orchestration Integration

**Status:** Proposed
**Date:** 2025-11-15
**Decision Makers:** Platform Team, DevOps Team
**Related ADRs:** ADR-0027 (AI Assistant), ADR-0032 (Community Distribution), ADR-0034 (Terminal Integration)

## Context and Problem Statement

The AI Assistant (ADR-0027) currently handles individual tasks but lacks sophisticated workflow orchestration capabilities for complex, multi-step operations. Users need to orchestrate deployments across multiple cloud providers (Qubinode, AWS, Google Cloud, Azure) and want extensibility through custom plugins for domain-specific automation workflows.

**Key Requirements:**

- Complex multi-step workflow orchestration with dependencies (DAGs)
- Multi-cloud deployment support (Qubinode, AWS, GCP, Azure)
- Custom plugin development capability for extensibility
- Optional feature (must not impact existing AI Assistant functionality)
- Visual workflow monitoring and debugging UI
- Integration with existing AI Assistant container architecture

## Decision Drivers

- Support for complex, multi-step workflows with dependencies and retries
- Multi-cloud portability without vendor lock-in
- Extensibility via custom plugins for domain-specific logic
- Mature, community-driven ecosystem with proven stability at scale
- Zero impact on existing users when disabled (optional feature flag)
- Visual workflow monitoring, debugging, and troubleshooting capabilities
- Alignment with container-first execution model (ADR-0001)

## Considered Options

1. **Apache Airflow** - Mature DAG-based workflow orchestration platform
1. **Prefect** - Modern Python workflow engine with hybrid execution
1. **Dagster** - Asset-based data orchestration platform
1. **Temporal** - Durable execution framework for long-running workflows
1. **Cloud-native solutions** - AWS Step Functions, Google Workflows, Azure Logic Apps
1. **Custom in-house orchestrator** - Build from scratch

## Decision Outcome

**Chosen option:** Apache Airflow as optional workflow orchestration engine

**Justification:**

- Most mature ecosystem (200+ community providers, 2000+ contributors)
- Proven stability at scale (used by Airbnb, Adobe, PayPal, 400+ organizations)
- Rich web UI for workflow visualization, monitoring, and debugging
- Extensive plugin ecosystem for cloud providers and infrastructure tools
- Portable containerized deployment (no vendor lock-in)
- Active development with regular security updates
- Strong community support and documentation

### Implementation Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Kubernetes Pod / Docker Compose               │
│                                                                  │
│  ┌──────────────────────┐  ┌──────────────────────────────────┐│
│  │  AI Assistant        │  │  Airflow (Optional Sidecar)      ││
│  │  Container           │  │                                  ││
│  │                      │  │  ┌────────────────────────────┐ ││
│  │  - Core AI Logic     │  │  │  Airflow Webserver (UI)    │ ││
│  │  - REST API (8000)   │  │  │  Port: 8080                │ ││
│  │  - RAG System        │  │  └────────────────────────────┘ ││
│  │  - Diagnostic Tools  │  │  ┌────────────────────────────┐ ││
│  │                      │  │  │  Airflow Scheduler         │ ││
│  └──────────────────────┘  │  │  (DAG execution engine)    │ ││
│           │                 │  └────────────────────────────┘ ││
│           │                 │  ┌────────────────────────────┐ ││
│           │                 │  │  Airflow Executor          │ ││
│           │                 │  │  (LocalExecutor/Celery)    │ ││
│           │                 │  └────────────────────────────┘ ││
│           │                 └──────────────────────────────────┘│
│           │                          │                           │
│           └──────────┬───────────────┘                           │
│                      │                                           │
│              ┌───────▼────────────┐                              │
│              │  Shared Volume     │                              │
│              │  - DAG files       │                              │
│              │  - Custom plugins  │                              │
│              │  - Execution logs  │                              │
│              │  - Configuration   │                              │
│              └────────────────────┘                              │
└──────────────────────────────────────────────────────────────────┘
                       │
                       ▼
              ┌────────────────────┐
              │   PostgreSQL DB    │
              │  (Airflow Metadata)│
              │  - DAG runs        │
              │  - Task instances  │
              │  - Connections     │
              │  - Variables       │
              └────────────────────┘
```

### Feature Flag Configuration

```bash
# Enable Airflow integration (default: false)
ENABLE_AIRFLOW=true

# Airflow configuration
AIRFLOW_HOME=/opt/airflow
AIRFLOW__WEBSERVER__WEB_SERVER_PORT=8080
AIRFLOW__CORE__EXECUTOR=LocalExecutor
AIRFLOW__CORE__LOAD_EXAMPLES=False
AIRFLOW__CORE__DAGS_FOLDER=/opt/airflow/dags
AIRFLOW__CORE__PLUGINS_FOLDER=/opt/airflow/plugins

# Database configuration
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@postgres:5432/airflow

# Security
AIRFLOW__WEBSERVER__SECRET_KEY=<generated-secret>
AIRFLOW__WEBSERVER__AUTHENTICATE=True
AIRFLOW__API__AUTH_BACKENDS=airflow.api.auth.backend.basic_auth
```

### Plugin Directory Structure

```
/opt/airflow/
├── dags/                           # DAG definitions
│   ├── qubinode_deploy.py         # Qubinode deployment workflow
│   ├── aws_infrastructure.py      # AWS infrastructure provisioning
│   ├── gcp_infrastructure.py      # GCP infrastructure provisioning
│   ├── azure_infrastructure.py    # Azure infrastructure provisioning
│   └── multi_cloud_sync.py        # Multi-cloud synchronization
├── plugins/                        # Custom plugins
│   ├── qubinode/
│   │   ├── __init__.py
│   │   ├── operators.py           # Custom Qubinode operators
│   │   ├── sensors.py             # Custom Qubinode sensors
│   │   └── hooks.py               # Custom Qubinode hooks
│   ├── aws_custom/
│   │   ├── __init__.py
│   │   └── operators.py
│   ├── gcp_custom/
│   │   ├── __init__.py
│   │   └── operators.py
│   └── azure_custom/
│       ├── __init__.py
│       └── operators.py
├── logs/                           # Execution logs
├── config/
│   └── airflow.cfg                # Airflow configuration
└── README.md                       # Plugin development guide
```

## Positive Consequences

- **Rich UI:** Web-based interface (port 8080) for workflow visualization, monitoring, and debugging
- **DAG Orchestration:** Complex multi-step workflows with dependencies, retries, and error handling
- **Extensibility:** 200+ community providers + custom plugin support for domain-specific logic
- **Multi-cloud:** Portable deployment across Qubinode, AWS, GCP, Azure without vendor lock-in
- **Zero Impact:** Existing AI Assistant users unaffected when feature flag disabled
- **Monitoring:** Built-in metrics, logging, alerting, and SLA tracking capabilities
- **Scheduling:** Cron-based, interval-based, and event-driven workflow triggers
- **Community:** Active ecosystem with regular updates, security patches, and best practices
- **Integration:** REST API for programmatic workflow management and triggering
- **Debugging:** Detailed task logs, execution history, and visual DAG representation

## Negative Consequences

- **Complexity:** Additional components (scheduler, webserver, executor, metadata DB)
- **Resources:** ~1.5GB additional container size, increased memory (2-4GB) and CPU usage
- **Maintenance:** Version compatibility management for Airflow core and plugins
- **Security:** Custom plugin execution requires sandboxing, validation, and security scanning
- **Learning Curve:** Users need to learn Airflow concepts (DAGs, operators, sensors, hooks)
- **Debugging:** Distributed workflow failures can be complex to troubleshoot
- **Database:** Requires PostgreSQL for metadata storage (additional operational overhead)
- **Port Management:** Additional port (8080) for Airflow UI requires firewall configuration

## Risks and Mitigations

| Risk                                                    | Impact   | Probability | Mitigation                                                              |
| ------------------------------------------------------- | -------- | ----------- | ----------------------------------------------------------------------- |
| Version compatibility drift between Airflow and plugins | High     | Medium      | Pin Airflow version, maintain compatibility matrix, automated testing   |
| Security vulnerabilities in custom plugins              | Critical | Medium      | Implement plugin sandboxing, static analysis in CI, code review process |
| Resource contention with AI Assistant                   | Medium   | High        | Set resource limits (CPU/memory), provide sizing guidance, monitoring   |
| Metadata DB failures causing workflow disruption        | High     | Low         | Regular backups, HA PostgreSQL setup, disaster recovery procedures      |
| Plugin API breaking changes in Airflow updates          | Medium   | Medium      | Semantic versioning, deprecation notices, migration guides              |
| Unauthorized access to Airflow UI                       | High     | Medium      | Enable authentication, RBAC, network policies, HTTPS                    |
| DAG parsing errors breaking scheduler                   | Medium   | Medium      | DAG validation in CI, error handling, monitoring alerts                 |

## Alternatives Considered

### Prefect

- **Pros:** Modern Python-first design, good developer experience, hybrid execution model, no metadata DB required
- **Cons:** Smaller ecosystem (50+ integrations vs 200+), less mature (founded 2018 vs 2014), fewer production deployments
- **Verdict:** Rejected - Airflow's maturity, ecosystem, and proven stability at scale are superior

### Dagster

- **Pros:** Asset-based paradigm, strong typing, excellent for data pipelines, modern architecture
- **Cons:** Focused on data engineering workflows, smaller community, steeper learning curve, less suitable for infrastructure
- **Verdict:** Rejected - not ideal for infrastructure orchestration and deployment workflows

### Temporal

- **Pros:** Durable execution guarantees, strong consistency, excellent fault tolerance, long-running workflows
- **Cons:** More complex architecture, smaller ecosystem, overkill for most workflow needs, steeper learning curve
- **Verdict:** Rejected - complexity doesn't match requirements, Airflow is simpler for our use case

### Cloud-native Step Functions (AWS, Google, Azure)

- **Pros:** Fully managed, tight cloud integration, no infrastructure management, serverless
- **Cons:** Vendor lock-in, conflicts with multi-cloud goal, proprietary APIs, different syntax per cloud
- **Verdict:** Rejected - incompatible with multi-cloud requirement and portability goals

### Custom In-house Orchestrator

- **Pros:** Full control, tailored to exact needs, no external dependencies
- **Cons:** High development cost (6-12 months), ongoing maintenance burden, no community support, reinventing wheel
- **Verdict:** Rejected - not worth the investment, Airflow provides everything needed

## Implementation Plan

### Phase 1: Core Integration (Weeks 1-2)

- [ ] Define `ENABLE_AIRFLOW` feature flag in configuration
- [ ] Create Airflow sidecar container Dockerfile
- [ ] Set up PostgreSQL metadata database
- [ ] Configure Docker Compose / Kubernetes manifests
- [ ] Implement health checks and startup orchestration
- [ ] Document installation and configuration

### Phase 2: Plugin Framework (Weeks 3-4)

- [ ] Design plugin directory structure and registration mechanism
- [ ] Create plugin development guide and templates
- [ ] Implement Qubinode custom operators and sensors
- [ ] Add AWS, GCP, Azure provider configurations
- [ ] Set up plugin validation and testing framework
- [ ] Document plugin development best practices

### Phase 3: Example DAGs (Week 5)

- [ ] Create Qubinode deployment DAG example
- [ ] Create multi-cloud infrastructure provisioning DAGs
- [ ] Add monitoring and alerting DAG examples
- [ ] Document DAG development patterns
- [ ] Provide troubleshooting guides

### Phase 4: Security & Monitoring (Week 6)

- [ ] Implement authentication and RBAC
- [ ] Set up plugin sandboxing and static analysis
- [ ] Configure logging and metrics collection
- [ ] Add security scanning to CI/CD pipeline
- [ ] Document security best practices

### Phase 5: Testing & Documentation (Week 7-8)

- [ ] Integration testing with AI Assistant
- [ ] Performance testing and resource optimization
- [ ] User acceptance testing
- [ ] Complete documentation and runbooks
- [ ] Create video tutorials and examples

## Success Metrics

| Metric                 | Target                                      | Measurement            |
| ---------------------- | ------------------------------------------- | ---------------------- |
| Adoption rate          | 30% of users enable Airflow within 3 months | Feature flag analytics |
| Custom plugins created | 10+ community plugins within 6 months       | Plugin registry        |
| Workflow success rate  | >95% successful DAG runs                    | Airflow metrics        |
| UI response time       | \<2 seconds for page loads                  | Performance monitoring |
| Resource overhead      | \<2GB additional memory when enabled        | Container metrics      |
| Security incidents     | Zero critical vulnerabilities               | Security scanning      |
| User satisfaction      | >4.0/5.0 rating                             | User surveys           |

## Community Ecosystem

### DAG Extensibility

Users can easily add custom DAGs by placing Python files in the `airflow/dags/` directory. Airflow automatically detects new DAGs within 5 minutes (configurable) without requiring a restart.

**Key Features:**

- **Hot-reload**: New DAGs detected automatically
- **Community Marketplace**: GitHub-based repository for sharing workflows
- **One-click Installation**: Simple CLI for importing community DAGs
- **RAG Workflow Templates**: Pre-built templates for document ingestion and processing

### Chat Interface Integration

The AI Assistant provides natural language workflow management:

```
User: "Can you ingest the new documentation files?"
AI: "I'll trigger the RAG document ingestion workflow..."
```

**Capabilities:**

- Trigger DAGs via natural language
- Monitor workflow status in chat
- List available workflows
- Get real-time execution updates

### RAG Workflow Integration

Pre-built workflows for RAG system management:

- Document ingestion pipeline
- Vector index updates
- Knowledge base synchronization
- Model fine-tuning workflows

### Bidirectional Learning System

**Airflow → RAG**: Workflow execution logs, error patterns, performance metrics, and success patterns are automatically injected into the RAG system, enabling continuous learning.

**RAG → Airflow**: The AI Assistant uses learned knowledge to:

- Generate optimized DAGs from natural language
- Predict and prevent workflow failures
- Auto-optimize existing workflows
- Suggest ADR updates based on patterns

**Continuous Improvement**: The system learns from every execution, automatically updating documentation (ADRs) and improving recommendations over time.

See [Bidirectional Learning Guide](../guides/airflow-rag-bidirectional-learning.md) for detailed information.

## References

- [Apache Airflow Official Documentation](https://airflow.apache.org/docs/)
- [Airflow Best Practices](https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html)
- [Airflow Community Providers](https://github.com/apache/airflow/tree/main/airflow/providers)
- [Kubernetes Sidecar Pattern](https://kubernetes.io/docs/concepts/workloads/pods/)
- [Community Ecosystem Guide](../guides/airflow-community-ecosystem.md)
- ADR-0001: Container-First Execution Model
- ADR-0027: CPU-Based AI Deployment Assistant Architecture
- ADR-0032: AI Assistant Community Distribution Strategy
- ADR-0034: AI Assistant Terminal Integration Strategy

## Appendix: Quick Start Guide

### Installing Airflow UI

```bash
# 1. Enable Airflow in configuration
export ENABLE_AIRFLOW=true

# 2. Start AI Assistant with Airflow
cd /opt/qubinode_navigator
docker-compose up -d

# 3. Wait for Airflow to initialize (30-60 seconds)
docker-compose logs -f airflow-webserver

# 4. Access Airflow UI
# Open browser to: http://localhost:8080
# Default credentials: admin / admin (change immediately!)

# 5. Verify Airflow is running
curl http://localhost:8080/health
```

### Creating Your First DAG

```python
# /opt/airflow/dags/hello_qubinode.py
from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'qubinode',
    'depends_on_past': False,
    'start_date': datetime(2025, 11, 15),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'hello_qubinode',
    default_args=default_args,
    description='A simple Qubinode workflow',
    schedule_interval=timedelta(days=1),
    catchup=False,
)

t1 = BashOperator(
    task_id='print_date',
    bash_command='date',
    dag=dag,
)

t2 = BashOperator(
    task_id='check_qubinode_status',
    bash_command='echo "Checking Qubinode status..."',
    dag=dag,
)

t1 >> t2  # t2 runs after t1
```

### Developing Custom Plugins

```python
# /opt/airflow/plugins/qubinode/operators.py
from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults

class QubinodeDeployOperator(BaseOperator):
    """
    Custom operator for Qubinode deployments
    """

    @apply_defaults
    def __init__(self, target_host, deployment_type, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target_host = target_host
        self.deployment_type = deployment_type

    def execute(self, context):
        self.log.info(f"Deploying to {self.target_host}")
        self.log.info(f"Deployment type: {self.deployment_type}")
        # Add your deployment logic here
        return "Deployment successful"
```

## Decision Log

- **2025-11-15:** Initial proposal created
- **Status:** Awaiting team review and approval
- **Next Review:** 2025-11-22
