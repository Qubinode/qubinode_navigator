---
title: Airflow Integration
parent: Explanation
nav_order: 2
---

# Apache Airflow Integration for Qubinode Navigator

This document provides a quick overview of the Apache Airflow integration with the Qubinode Navigator AI Assistant.

> **Documentation status**
>
> - Validation: `IN PROGRESS` – Airflow integration is under active development and may evolve.
> - Last reviewed: 2025-11-21
> - Community: If you deploy this successfully or find gaps, please help improve this guide via [Contributing to docs](../how-to/contribute.md).

## 📋 Overview

Apache Airflow has been integrated as an **optional** workflow orchestration engine to enable complex, multi-step deployments across multiple cloud providers (Qubinode, AWS, Google Cloud, Azure).

## 🎯 Key Features

- **DAG-based Workflows**: Define complex deployment workflows with dependencies
- **Web UI**: Visual workflow monitoring and debugging (port 8888)
- **Custom Plugins**: Extensible plugin system for domain-specific logic
- **Multi-Cloud**: Deploy to Qubinode, AWS, GCP, and Azure from a single interface
- **Optional**: Feature flag controlled - zero impact when disabled
- **Sidecar Architecture**: Runs alongside AI Assistant without modifying core functionality

## 🚀 Quick Start

### 1. Enable Airflow

```bash
export ENABLE_AIRFLOW=true
```

### 2. Start Services

```bash
cd /opt/qubinode_navigator
docker-compose -f docker-compose-airflow.yml up -d
```

### 3. Access UI

Open browser to: **http://localhost:8888**

- Username: `admin`
- Password: `admin` (change immediately!)

## 📁 Documentation

- **[ADR-0036](https://github.com/Qubinode/qubinode_navigator/blob/main/docs/adrs/adr-0036-apache-airflow-workflow-orchestration-integration.md)** - Architectural decision record
- **[Integration Guide](../tutorials/airflow-integration-guide.md)** - Detailed installation and configuration
- **[Plugin Development](./airflow-integration-guide.md#creating-custom-plugins)** - Custom plugin creation guide

## 🔧 Directory Structure

```
airflow/
├── dags/                    # Workflow definitions
│   ├── qubinode_deploy.py
│   ├── aws_infrastructure.py
│   └── multi_cloud_sync.py
├── plugins/                 # Custom plugins
│   ├── qubinode/
│   ├── aws_custom/
│   └── gcp_custom/
├── logs/                    # Execution logs
└── config/                  # Configuration files
```

## 📊 Example Use Cases

### 1. Qubinode Deployment Workflow

```python
from airflow import DAG
from airflow.operators.bash import BashOperator

dag = DAG('qubinode_deploy', ...)

validate = BashOperator(task_id='validate', ...)
deploy = BashOperator(task_id='deploy', ...)
verify = BashOperator(task_id='verify', ...)

validate >> deploy >> verify
```

### 2. Multi-Cloud Infrastructure

```python
from airflow import DAG
from airflow.operators.python import BranchPythonOperator

dag = DAG('multi_cloud_deploy', ...)

branch = BranchPythonOperator(task_id='choose_cloud', ...)
deploy_aws = BashOperator(task_id='deploy_aws', ...)
deploy_gcp = BashOperator(task_id='deploy_gcp', ...)
deploy_azure = BashOperator(task_id='deploy_azure', ...)

branch >> [deploy_aws, deploy_gcp, deploy_azure]
```

## 🔌 Custom Plugin Example

```python
from airflow.models import BaseOperator

class QubinodeDeployOperator(BaseOperator):
    def __init__(self, target_host, deployment_type, **kwargs):
        super().__init__(**kwargs)
        self.target_host = target_host
        self.deployment_type = deployment_type

    def execute(self, context):
        # Your deployment logic here
        return f"Deployed to {self.target_host}"
```

## 🛠️ Configuration

### Environment Variables

```bash
# Enable Airflow
ENABLE_AIRFLOW=true

# Airflow settings
AIRFLOW_HOME=/opt/airflow
AIRFLOW__WEBSERVER__WEB_SERVER_PORT=8888
AIRFLOW__CORE__EXECUTOR=LocalExecutor
AIRFLOW__CORE__LOAD_EXAMPLES=False

# Database
AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@postgres:5432/airflow
```

## 📈 Resource Requirements

| Component                | CPU           | Memory    | Storage  |
| ------------------------ | ------------- | --------- | -------- |
| Airflow Webserver        | 1 core        | 1GB       | -        |
| Airflow Scheduler        | 1 core        | 1GB       | -        |
| PostgreSQL               | 0.5 core      | 512MB     | 10GB     |
| **Total (when enabled)** | **2.5 cores** | **2.5GB** | **10GB** |

## 🔒 Security Considerations

- Change default admin password immediately
- Enable RBAC for multi-user environments
- Use secrets backend for sensitive data
- Implement plugin sandboxing
- Enable HTTPS for production deployments
- Regular security updates

## 🐛 Troubleshooting

### UI Not Accessible

```bash
# Check services
docker-compose ps

# View logs
docker-compose logs airflow-webserver

# Verify port
netstat -tlnp | grep 8888
```

### DAGs Not Appearing

```bash
# Check DAG folder
ls -la airflow/dags/

# Validate DAGs
docker-compose exec airflow-webserver airflow dags list

# Check for errors
docker-compose exec airflow-webserver airflow dags list-import-errors
```

### Database Connection Issues

```bash
# Test database
docker-compose exec postgres psql -U airflow -d airflow -c "SELECT 1;"

# Reset database
docker-compose down -v
docker-compose up -d
```

## 📚 Additional Resources

- **Apache Airflow Docs**: https://airflow.apache.org/docs/
- **Best Practices**: https://airflow.apache.org/docs/apache-airflow/stable/best-practices.html
- **Community Providers**: https://github.com/apache/airflow/tree/main/airflow/providers
- **Slack Community**: https://apache-airflow-slack.herokuapp.com/

## 🎯 Success Metrics

| Metric                 | Target              |
| ---------------------- | ------------------- |
| Adoption Rate          | 30% within 3 months |
| Workflow Success Rate  | >95%                |
| UI Response Time       | \<2 seconds         |
| Custom Plugins Created | 10+ within 6 months |

## 🗺️ Roadmap

### Phase 1: Core Integration (Weeks 1-2) ✅

- [x] ADR documentation
- [x] Installation guide
- [x] Docker Compose configuration

### Phase 2: Plugin Framework (Weeks 3-4)

- [ ] Qubinode custom operators
- [ ] AWS/GCP/Azure provider configs
- [ ] Plugin validation framework

### Phase 3: Example DAGs (Week 5)

- [ ] Qubinode deployment DAG
- [ ] Multi-cloud provisioning DAGs
- [ ] Monitoring DAGs

### Phase 4: Security & Monitoring (Week 6)

- [ ] Authentication and RBAC
- [ ] Plugin sandboxing
- [ ] Metrics collection

### Phase 5: Testing & Documentation (Weeks 7-8)

- [ ] Integration testing
- [ ] Performance optimization
- [ ] Video tutorials

## 🤝 Contributing

We welcome contributions! Areas for contribution:

1. **Custom Plugins**: Create plugins for specific cloud providers or tools
1. **Example DAGs**: Share workflow patterns and best practices
1. **Documentation**: Improve guides and tutorials
1. **Testing**: Add integration and performance tests
1. **Bug Fixes**: Report and fix issues

## 📞 Support

- **GitHub Issues**: https://github.com/Qubinode/qubinode_navigator/issues
- **Documentation**: [Airflow Integration Guide](../tutorials/airflow-integration-guide.md)
- **ADR**: [ADR-0036](https://github.com/Qubinode/qubinode_navigator/blob/main/docs/adrs/adr-0036-apache-airflow-workflow-orchestration-integration.md)

## 📄 License

This integration follows the same license as Qubinode Navigator. Apache Airflow is licensed under Apache License 2.0.

______________________________________________________________________

**Status**: Proposed (ADR-0036)
**Last Updated**: 2025-11-15
**Maintainers**: Platform Team, DevOps Team
