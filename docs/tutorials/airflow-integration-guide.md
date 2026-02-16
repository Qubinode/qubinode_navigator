---
title: Airflow Integration Guide
parent: Tutorials
nav_order: 5
---

# Apache Airflow Integration Guide

This guide provides step-by-step instructions for integrating Apache Airflow with the Qubinode Navigator AI Assistant.

## Table of Contents

1. [Prerequisites](#prerequisites)
1. [Installation Methods](#installation-methods)
1. [Starting Airflow UI](#starting-airflow-ui)
1. [Configuration](#configuration)
1. [Creating Custom Plugins](#creating-custom-plugins)
1. [Example DAGs](#example-dags)
1. [Troubleshooting](#troubleshooting)

## Prerequisites

- Docker or Podman installed
- Docker Compose or Podman Compose
- At least 4GB free RAM
- Ports 8888 (Airflow UI) and 5432 (PostgreSQL) available
- AI Assistant container running (see ADR-0027)

## Installation Methods

### Method 1: Docker Compose (Recommended)

Create a `docker-compose-airflow.yml` file:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: airflow
      POSTGRES_PASSWORD: airflow
      POSTGRES_DB: airflow
    volumes:
      - postgres-db-volume:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "airflow"]
      interval: 10s
      retries: 5
      start_period: 5s
    restart: always

  airflow-webserver:
    image: apache/airflow:2.8.0-python3.11
    command: webserver
    ports:
      - "8888:8888"
    environment:
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@postgres/airflow
      AIRFLOW__CORE__FERNET_KEY: ''
      AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION: 'true'
      AIRFLOW__CORE__LOAD_EXAMPLES: 'false'
      AIRFLOW__API__AUTH_BACKENDS: 'airflow.api.auth.backend.basic_auth,airflow.api.auth.backend.session'
      AIRFLOW__WEBSERVER__SECRET_KEY: 'your-secret-key-here'
      _AIRFLOW_DB_MIGRATE: 'true'
      _AIRFLOW_WWW_USER_CREATE: 'true'
      _AIRFLOW_WWW_USER_USERNAME: admin
      _AIRFLOW_WWW_USER_PASSWORD: admin
    volumes:
      - ./airflow/dags:/opt/airflow/dags
      - ./airflow/logs:/opt/airflow/logs
      - ./airflow/plugins:/opt/airflow/plugins
      - ./airflow/config:/opt/airflow/config
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "--fail", "http://localhost:8888/health"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s
    restart: always

  airflow-scheduler:
    image: apache/airflow:2.8.0-python3.11
    command: scheduler
    environment:
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@postgres/airflow
      AIRFLOW__CORE__FERNET_KEY: ''
      AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION: 'true'
      AIRFLOW__CORE__LOAD_EXAMPLES: 'false'
    volumes:
      - ./airflow/dags:/opt/airflow/dags
      - ./airflow/logs:/opt/airflow/logs
      - ./airflow/plugins:/opt/airflow/plugins
      - ./airflow/config:/opt/airflow/config
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "airflow", "jobs", "check", "--job-type", "SchedulerJob", "--hostname", "$${HOSTNAME}"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 30s
    restart: always

  # Optional: AI Assistant integration
  ai-assistant:
    image: quay.io/takinosh/qubinode-ai-assistant:latest
    ports:
      - "8000:8000"
    environment:
      ENABLE_AIRFLOW: "true"
      AIRFLOW_API_URL: "http://airflow-webserver:8888/api/v1"
    volumes:
      - ./airflow/dags:/opt/airflow/dags:ro
    depends_on:
      airflow-webserver:
        condition: service_healthy
    restart: always

volumes:
  postgres-db-volume:
```

### Method 2: Standalone Installation

```bash
#!/bin/bash
# install-airflow.sh

set -e

echo "Installing Apache Airflow..."

# Set Airflow home
export AIRFLOW_HOME=~/airflow
mkdir -p $AIRFLOW_HOME

# Install Airflow
AIRFLOW_VERSION=2.8.0
PYTHON_VERSION="$(python3 --version | cut -d " " -f 2 | cut -d "." -f 1-2)"
CONSTRAINT_URL="https://raw.githubusercontent.com/apache/airflow/constraints-${AIRFLOW_VERSION}/constraints-${PYTHON_VERSION}.txt"

pip3 install "apache-airflow==${AIRFLOW_VERSION}" --constraint "${CONSTRAINT_URL}"

# Install providers
pip3 install apache-airflow-providers-amazon
pip3 install apache-airflow-providers-google
pip3 install apache-airflow-providers-microsoft-azure

# Initialize database
airflow db init

# Create admin user
airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin

echo "Airflow installed successfully!"
echo "Start with: airflow webserver -p 8080 & airflow scheduler"
```

## Starting Airflow UI

### Using Docker Compose

```bash
# 1. Create directory structure
mkdir -p airflow/{dags,logs,plugins,config}

# 2. Start services
docker-compose -f docker-compose-airflow.yml up -d

# 3. Check logs
docker-compose -f docker-compose-airflow.yml logs -f airflow-webserver

# 4. Access UI
# Open browser: http://localhost:8888
# Username: admin
# Password: admin
```

### Using Standalone Installation

```bash
# Terminal 1: Start webserver
export AIRFLOW_HOME=~/airflow
airflow webserver --port 8080

# Terminal 2: Start scheduler
export AIRFLOW_HOME=~/airflow
airflow scheduler
```

### Using systemd (Production)

Create `/etc/systemd/system/airflow-webserver.service`:

```ini
[Unit]
Description=Airflow webserver daemon
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Environment="AIRFLOW_HOME=/opt/airflow"
User=airflow
Group=airflow
Type=simple
ExecStart=/usr/local/bin/airflow webserver --port 8080
Restart=on-failure
RestartSec=5s
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/airflow-scheduler.service`:

```ini
[Unit]
Description=Airflow scheduler daemon
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Environment="AIRFLOW_HOME=/opt/airflow"
User=airflow
Group=airflow
Type=simple
ExecStart=/usr/local/bin/airflow scheduler
Restart=on-failure
RestartSec=5s
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Enable and start services:

```bash
sudo systemctl daemon-reload
sudo systemctl enable airflow-webserver airflow-scheduler
sudo systemctl start airflow-webserver airflow-scheduler
sudo systemctl status airflow-webserver airflow-scheduler
```

## Configuration

### Environment Variables

```bash
# Core settings
export AIRFLOW_HOME=/opt/airflow
export AIRFLOW__CORE__EXECUTOR=LocalExecutor
export AIRFLOW__CORE__LOAD_EXAMPLES=False
export AIRFLOW__CORE__DAGS_FOLDER=/opt/airflow/dags
export AIRFLOW__CORE__PLUGINS_FOLDER=/opt/airflow/plugins

# Database
export AIRFLOW__DATABASE__SQL_ALCHEMY_CONN=postgresql+psycopg2://airflow:airflow@localhost:5432/airflow

# Webserver
export AIRFLOW__WEBSERVER__WEB_SERVER_PORT=8080
export AIRFLOW__WEBSERVER__SECRET_KEY=$(openssl rand -hex 32)
export AIRFLOW__WEBSERVER__AUTHENTICATE=True
export AIRFLOW__WEBSERVER__RBAC=True

# Security
export AIRFLOW__API__AUTH_BACKENDS=airflow.api.auth.backend.basic_auth

# Logging
export AIRFLOW__LOGGING__BASE_LOG_FOLDER=/opt/airflow/logs
export AIRFLOW__LOGGING__REMOTE_LOGGING=False
```

### airflow.cfg Customization

```ini
[core]
dags_folder = /opt/airflow/dags
plugins_folder = /opt/airflow/plugins
executor = LocalExecutor
load_examples = False
parallelism = 32
dag_concurrency = 16
max_active_runs_per_dag = 16

[webserver]
web_server_port = 8080
authenticate = True
rbac = True
expose_config = False

[scheduler]
dag_dir_list_interval = 300
catchup_by_default = False
max_threads = 2

[api]
auth_backends = airflow.api.auth.backend.basic_auth

[logging]
base_log_folder = /opt/airflow/logs
remote_logging = False
logging_level = INFO
```

## Creating Custom Plugins

### Plugin Structure

```
airflow/plugins/
└── qubinode/
    ├── __init__.py
    ├── operators/
    │   ├── __init__.py
    │   ├── deploy_operator.py
    │   └── validation_operator.py
    ├── sensors/
    │   ├── __init__.py
    │   └── deployment_sensor.py
    ├── hooks/
    │   ├── __init__.py
    │   └── qubinode_hook.py
    └── README.md
```

### Example: Qubinode Deploy Operator

```python
# airflow/plugins/qubinode/operators/deploy_operator.py

from airflow.models import BaseOperator
from airflow.utils.decorators import apply_defaults
import subprocess
import logging

class QubinodeDeployOperator(BaseOperator):
    """
    Operator to deploy Qubinode infrastructure

    :param target_host: Target host for deployment
    :param deployment_type: Type of deployment (kvm, openshift, etc.)
    :param config_file: Path to configuration file
    """

    template_fields = ('target_host', 'config_file')
    ui_color = '#4CAF50'

    @apply_defaults
    def __init__(
        self,
        target_host: str,
        deployment_type: str = 'kvm',
        config_file: str = None,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.target_host = target_host
        self.deployment_type = deployment_type
        self.config_file = config_file
        self.log = logging.getLogger(__name__)

    def execute(self, context):
        self.log.info(f"Starting Qubinode deployment to {self.target_host}")
        self.log.info(f"Deployment type: {self.deployment_type}")

        # Build deployment command
        cmd = [
            '/opt/qubinode_navigator/setup.sh',
            '--host', self.target_host,
            '--type', self.deployment_type
        ]

        if self.config_file:
            cmd.extend(['--config', self.config_file])

        # Execute deployment
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            self.log.info(f"Deployment output: {result.stdout}")
            return {
                'status': 'success',
                'target_host': self.target_host,
                'output': result.stdout
            }

        except subprocess.CalledProcessError as e:
            self.log.error(f"Deployment failed: {e.stderr}")
            raise
```

### Example: Deployment Sensor

```python
# airflow/plugins/qubinode/sensors/deployment_sensor.py

from airflow.sensors.base import BaseSensorOperator
from airflow.utils.decorators import apply_defaults
import subprocess

class QubinodeDeploymentSensor(BaseSensorOperator):
    """
    Sensor to check if Qubinode deployment is complete

    :param target_host: Target host to check
    :param timeout: Sensor timeout in seconds
    """

    template_fields = ('target_host',)

    @apply_defaults
    def __init__(
        self,
        target_host: str,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.target_host = target_host

    def poke(self, context):
        """Check if deployment is complete"""
        self.log.info(f"Checking deployment status on {self.target_host}")

        try:
            # Check if deployment is complete
            result = subprocess.run(
                ['ssh', self.target_host, 'systemctl is-active libvirtd'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and 'active' in result.stdout:
                self.log.info(f"Deployment complete on {self.target_host}")
                return True
            else:
                self.log.info(f"Deployment still in progress...")
                return False

        except Exception as e:
            self.log.warning(f"Error checking deployment: {e}")
            return False
```

## Example DAGs

### Simple Qubinode Deployment DAG

```python
# airflow/dags/qubinode_simple_deploy.py

from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'qubinode',
    'depends_on_past': False,
    'start_date': datetime(2025, 11, 15),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'qubinode_simple_deploy',
    default_args=default_args,
    description='Simple Qubinode deployment workflow',
    schedule_interval=None,  # Manual trigger only
    catchup=False,
    tags=['qubinode', 'deployment'],
)

# Pre-deployment validation
validate = BashOperator(
    task_id='validate_prerequisites',
    bash_command='cd /opt/qubinode_navigator && ./scripts/validate.sh',
    dag=dag,
)

# Deploy Qubinode
deploy = BashOperator(
    task_id='deploy_qubinode',
    bash_command='cd /opt/qubinode_navigator && ./setup.sh',
    dag=dag,
)

# Post-deployment verification
verify = BashOperator(
    task_id='verify_deployment',
    bash_command='systemctl is-active libvirtd && virsh list --all',
    dag=dag,
)

# Notification
notify = BashOperator(
    task_id='send_notification',
    bash_command='echo "Deployment complete!" | mail -s "Qubinode Deployed" admin@example.com',
    dag=dag,
)

validate >> deploy >> verify >> notify
```

### Multi-Cloud Deployment DAG

```python
# airflow/dags/multi_cloud_deploy.py

from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'qubinode',
    'depends_on_past': False,
    'start_date': datetime(2025, 11, 15),
    'email_on_failure': True,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'multi_cloud_deploy',
    default_args=default_args,
    description='Multi-cloud deployment orchestration',
    schedule_interval=None,
    catchup=False,
    tags=['multi-cloud', 'deployment'],
)

def determine_cloud_provider(**context):
    """Determine which cloud provider to use"""
    provider = context['dag_run'].conf.get('provider', 'qubinode')
    return f'deploy_{provider}'

branch = BranchPythonOperator(
    task_id='determine_provider',
    python_callable=determine_cloud_provider,
    dag=dag,
)

deploy_qubinode = BashOperator(
    task_id='deploy_qubinode',
    bash_command='cd /opt/qubinode_navigator && ./setup.sh',
    dag=dag,
)

deploy_aws = BashOperator(
    task_id='deploy_aws',
    bash_command='terraform apply -auto-approve -var-file=aws.tfvars',
    dag=dag,
)

deploy_gcp = BashOperator(
    task_id='deploy_gcp',
    bash_command='terraform apply -auto-approve -var-file=gcp.tfvars',
    dag=dag,
)

deploy_azure = BashOperator(
    task_id='deploy_azure',
    bash_command='terraform apply -auto-approve -var-file=azure.tfvars',
    dag=dag,
)

branch >> [deploy_qubinode, deploy_aws, deploy_gcp, deploy_azure]
```

## Troubleshooting

### Common Issues

#### 1. Airflow UI not accessible

```bash
# Check if webserver is running
docker-compose ps airflow-webserver

# Check logs
docker-compose logs airflow-webserver

# Verify port is listening
netstat -tlnp | grep 8888

# Check firewall
sudo firewall-cmd --list-ports
sudo firewall-cmd --add-port=8888/tcp --permanent
sudo firewall-cmd --reload
```

#### 2. Database connection errors

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Test database connection
docker-compose exec postgres psql -U airflow -d airflow -c "SELECT 1;"

# Reset database
docker-compose down -v
docker-compose up -d
```

#### 3. DAGs not appearing

```bash
# Check DAG folder permissions
ls -la airflow/dags/

# Validate DAG syntax
docker-compose exec airflow-webserver airflow dags list

# Check for parsing errors
docker-compose exec airflow-webserver airflow dags list-import-errors
```

#### 4. Scheduler not running tasks

```bash
# Check scheduler logs
docker-compose logs airflow-scheduler

# Verify scheduler is healthy
docker-compose exec airflow-scheduler airflow jobs check --job-type SchedulerJob

# Restart scheduler
docker-compose restart airflow-scheduler
```

### Health Check Commands

```bash
# Check all services
docker-compose ps

# Check Airflow version
docker-compose exec airflow-webserver airflow version

# List DAGs
docker-compose exec airflow-webserver airflow dags list

# Test DAG
docker-compose exec airflow-webserver airflow dags test <dag_id> <execution_date>

# Check connections
docker-compose exec airflow-webserver airflow connections list

# Check variables
docker-compose exec airflow-webserver airflow variables list
```

## Next Steps

1. Review [ADR-0036](https://github.com/Qubinode/qubinode_navigator/blob/main/docs/adrs/adr-0036-apache-airflow-workflow-orchestration-integration.md) for architectural decisions
1. Explore [Airflow Documentation](https://airflow.apache.org/docs/)
1. Join [Airflow Slack Community](https://apache-airflow-slack.herokuapp.com/)
1. Create custom plugins for your use case
1. Set up monitoring and alerting

## Support

- GitHub Issues: https://github.com/Qubinode/qubinode_navigator/issues
- Airflow Documentation: https://airflow.apache.org/docs/
- Community Slack: https://apache-airflow-slack.herokuapp.com/
