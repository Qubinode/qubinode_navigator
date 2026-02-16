---
title: Airflow Community Ecosystem
parent: Guides
nav_order: 4
---

# Airflow Community Ecosystem & RAG Workflow Integration

## Overview

This guide explains how users can contribute DAGs, share workflows, and integrate RAG (Retrieval-Augmented Generation) capabilities into the Airflow ecosystem for Qubinode Navigator.

## Table of Contents

1. [Adding Custom DAGs](#adding-custom-dags)
1. [Community DAG Marketplace](#community-dag-marketplace)
1. [RAG Workflow Integration](#rag-workflow-integration)
1. [Chat Interface for Workflow Management](#chat-interface-for-workflow-management)
1. [Community Contribution Guidelines](#community-contribution-guidelines)

______________________________________________________________________

## Adding Custom DAGs

### Simple DAG Addition

Users can easily add new DAGs by placing Python files in the `airflow/dags/` directory:

```bash
# 1. Create your DAG file
cat > airflow/dags/my_custom_workflow.py << 'EOF'
from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'community',
    'start_date': datetime(2025, 11, 15),
    'retries': 1,
}

dag = DAG(
    'my_custom_workflow',
    default_args=default_args,
    description='My custom deployment workflow',
    schedule_interval=None,
    tags=['community', 'custom'],
)

task1 = BashOperator(
    task_id='my_task',
    bash_command='echo "Hello from my custom DAG!"',
    dag=dag,
)
EOF

# 2. Airflow automatically detects new DAGs (within 5 minutes)
# No restart required!

# 3. Verify DAG is loaded
docker-compose exec airflow-webserver airflow dags list | grep my_custom_workflow
```

### Hot-Reload Feature

Airflow automatically detects new DAGs without restart:

- **Detection Interval**: 300 seconds (5 minutes) by default
- **Configurable**: Set `AIRFLOW__SCHEDULER__DAG_DIR_LIST_INTERVAL` to change
- **Instant Testing**: Use `airflow dags test` for immediate validation

```bash
# Test DAG immediately without waiting for scheduler
docker-compose exec airflow-webserver airflow dags test my_custom_workflow 2025-11-15
```

______________________________________________________________________

## Community DAG Marketplace

### Vision: GitHub-Based DAG Repository

Create a community-driven marketplace where users can share and discover DAGs:

```
qubinode-airflow-dags/
├── README.md
├── marketplace/
│   ├── infrastructure/
│   │   ├── aws_ec2_provisioning.py
│   │   ├── gcp_gke_cluster.py
│   │   ├── azure_vm_deployment.py
│   │   └── qubinode_kvm_setup.py
│   ├── data_pipelines/
│   │   ├── postgres_backup.py
│   │   ├── redis_sync.py
│   │   └── s3_data_transfer.py
│   ├── monitoring/
│   │   ├── health_check_workflow.py
│   │   ├── log_aggregation.py
│   │   └── metric_collection.py
│   └── ai_workflows/
│       ├── rag_document_ingestion.py
│       ├── model_training_pipeline.py
│       └── inference_deployment.py
├── plugins/
│   └── community_operators/
└── examples/
    └── getting_started/
```

### DAG Installation CLI

```bash
#!/bin/bash
# install-dag.sh - Community DAG installer

DAG_REPO="https://github.com/Qubinode/airflow-dags"
DAG_NAME=$1
CATEGORY=$2

# Download DAG from marketplace
curl -o "airflow/dags/${DAG_NAME}.py" \
  "${DAG_REPO}/raw/main/marketplace/${CATEGORY}/${DAG_NAME}.py"

# Validate DAG syntax
docker-compose exec airflow-webserver python -m py_compile "/opt/airflow/dags/${DAG_NAME}.py"

echo "✅ DAG '${DAG_NAME}' installed successfully!"
echo "🔄 It will appear in Airflow UI within 5 minutes"
```

### Usage Example

```bash
# Install a community DAG
./install-dag.sh rag_document_ingestion ai_workflows

# Browse available DAGs
curl https://api.github.com/repos/Qubinode/airflow-dags/contents/marketplace
```

### DAG Metadata Standard

Community DAGs should include metadata for discoverability:

```python
"""
DAG: RAG Document Ingestion Pipeline
Author: @username
Category: AI Workflows
Tags: rag, ai-assistant, document-processing
Description: Automated pipeline for ingesting documents into RAG system
Version: 1.0.0
Dependencies: apache-airflow-providers-postgres, langchain
License: Apache-2.0
"""

from airflow import DAG
# ... rest of DAG definition
```

______________________________________________________________________

## RAG Workflow Integration

### Architecture: AI Assistant + Airflow + RAG

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interface                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Chat UI      │  │ Airflow UI   │  │ API Endpoints    │  │
│  │ (Terminal)   │  │ (Web)        │  │ (REST/GraphQL)   │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└────────────┬──────────────┬────────────────┬────────────────┘
             │              │                │
             ▼              ▼                ▼
┌────────────────────────────────────────────────────────────┐
│                   AI Assistant Container                    │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  RAG System (LlamaIndex/LangChain)                   │  │
│  │  - Document Store (5,199 docs)                       │  │
│  │  - Vector Database (ChromaDB/FAISS)                  │  │
│  │  - Embedding Model (sentence-transformers)           │  │
│  │  - LLM (IBM Granite-4.0-Micro)                       │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                 │
│                           ▼                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Airflow Integration Layer                           │  │
│  │  - Trigger DAGs via API                              │  │
│  │  - Monitor workflow status                           │  │
│  │  - Retrieve execution logs                           │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────┬───────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────┐
│              Airflow Sidecar Container                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  RAG Workflow DAGs                                   │  │
│  │  - Document ingestion pipeline                       │  │
│  │  - Vector index updates                              │  │
│  │  - Knowledge base synchronization                    │  │
│  │  - Model fine-tuning workflows                       │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

### Example: RAG Document Ingestion DAG

```python
# airflow/dags/rag_document_ingestion.py

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.http.operators.http import SimpleHttpOperator
from datetime import datetime, timedelta
import json

default_args = {
    'owner': 'ai-assistant',
    'depends_on_past': False,
    'start_date': datetime(2025, 11, 15),
    'email_on_failure': True,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'rag_document_ingestion',
    default_args=default_args,
    description='Ingest documents into RAG system',
    schedule_interval='@daily',  # Run daily
    catchup=False,
    tags=['rag', 'ai-assistant', 'document-processing'],
)

def scan_for_new_documents(**context):
    """Scan for new documents to ingest"""
    import os
    from pathlib import Path

    doc_dir = Path('/opt/documents/incoming')
    new_docs = [str(f) for f in doc_dir.glob('**/*') if f.is_file()]

    context['task_instance'].xcom_push(key='new_documents', value=new_docs)
    return len(new_docs)

def chunk_documents(**context):
    """Split documents into chunks for embedding"""
    from langchain.text_splitter import RecursiveCharacterTextSplitter

    docs = context['task_instance'].xcom_pull(key='new_documents')
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
    )

    chunks = []
    for doc_path in docs:
        with open(doc_path, 'r') as f:
            text = f.read()
            doc_chunks = splitter.split_text(text)
            chunks.extend([{
                'text': chunk,
                'source': doc_path,
                'chunk_id': i
            } for i, chunk in enumerate(doc_chunks)])

    context['task_instance'].xcom_push(key='chunks', value=chunks)
    return len(chunks)

def generate_embeddings(**context):
    """Generate embeddings for document chunks"""
    from sentence_transformers import SentenceTransformer

    chunks = context['task_instance'].xcom_pull(key='chunks')
    model = SentenceTransformer('all-MiniLM-L6-v2')

    texts = [chunk['text'] for chunk in chunks]
    embeddings = model.encode(texts)

    # Add embeddings to chunks
    for i, chunk in enumerate(chunks):
        chunk['embedding'] = embeddings[i].tolist()

    context['task_instance'].xcom_push(key='embedded_chunks', value=chunks)
    return len(chunks)

def store_in_vector_db(**context):
    """Store embeddings in vector database"""
    import chromadb

    chunks = context['task_instance'].xcom_pull(key='embedded_chunks')

    client = chromadb.HttpClient(host='localhost', port=8001)
    collection = client.get_or_create_collection('qubinode_docs')

    collection.add(
        embeddings=[chunk['embedding'] for chunk in chunks],
        documents=[chunk['text'] for chunk in chunks],
        metadatas=[{
            'source': chunk['source'],
            'chunk_id': chunk['chunk_id']
        } for chunk in chunks],
        ids=[f"{chunk['source']}_{chunk['chunk_id']}" for chunk in chunks]
    )

    return len(chunks)

def notify_ai_assistant(**context):
    """Notify AI Assistant that new documents are available"""
    import requests

    num_chunks = context['task_instance'].xcom_pull(task_ids='store_in_vector_db')

    response = requests.post(
        'http://ai-assistant:8000/api/rag/refresh',
        json={'num_new_chunks': num_chunks}
    )

    return response.json()

# Define tasks
scan_task = PythonOperator(
    task_id='scan_for_new_documents',
    python_callable=scan_for_new_documents,
    dag=dag,
)

chunk_task = PythonOperator(
    task_id='chunk_documents',
    python_callable=chunk_documents,
    dag=dag,
)

embed_task = PythonOperator(
    task_id='generate_embeddings',
    python_callable=generate_embeddings,
    dag=dag,
)

store_task = PythonOperator(
    task_id='store_in_vector_db',
    python_callable=store_in_vector_db,
    dag=dag,
)

notify_task = PythonOperator(
    task_id='notify_ai_assistant',
    python_callable=notify_ai_assistant,
    dag=dag,
)

# Define workflow
scan_task >> chunk_task >> embed_task >> store_task >> notify_task
```

### RAG Workflow Templates

Create reusable templates for common RAG operations:

```python
# airflow/dags/templates/rag_base_template.py

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

class RAGWorkflowTemplate:
    """Base template for RAG workflows"""

    def __init__(self, dag_id, description, schedule_interval='@daily'):
        self.default_args = {
            'owner': 'ai-assistant',
            'depends_on_past': False,
            'start_date': datetime(2025, 11, 15),
            'email_on_failure': True,
            'retries': 2,
            'retry_delay': timedelta(minutes=5),
        }

        self.dag = DAG(
            dag_id,
            default_args=self.default_args,
            description=description,
            schedule_interval=schedule_interval,
            catchup=False,
            tags=['rag', 'ai-assistant', 'template'],
        )

    def create_ingestion_pipeline(self, source_type='filesystem'):
        """Create document ingestion pipeline"""
        # Implementation here
        pass

    def create_update_pipeline(self):
        """Create vector index update pipeline"""
        # Implementation here
        pass

    def create_cleanup_pipeline(self):
        """Create old document cleanup pipeline"""
        # Implementation here
        pass
```

______________________________________________________________________

## Chat Interface for Workflow Management

### Natural Language DAG Triggering

Integrate Airflow with the AI Assistant's chat interface:

```python
# ai-assistant/src/airflow_chat_integration.py

import requests
from typing import Dict, Any

class AirflowChatInterface:
    """Chat interface for Airflow workflow management"""

    def __init__(self, airflow_url='http://airflow-webserver:8080'):
        self.airflow_url = airflow_url
        self.auth = ('admin', 'admin')  # Use proper auth in production

    def trigger_dag_from_chat(self, user_message: str) -> Dict[str, Any]:
        """
        Parse user message and trigger appropriate DAG

        Examples:
        - "Deploy to AWS"
        - "Ingest new documents"
        - "Run the multi-cloud sync"
        - "Update the RAG knowledge base"
        """
        # Use LLM to parse intent
        intent = self.parse_intent(user_message)

        if intent['action'] == 'deploy':
            return self.trigger_deployment(intent['target'])
        elif intent['action'] == 'ingest':
            return self.trigger_ingestion()
        elif intent['action'] == 'sync':
            return self.trigger_sync(intent['target'])
        elif intent['action'] == 'update':
            return self.trigger_update(intent['component'])

    def parse_intent(self, message: str) -> Dict[str, str]:
        """Use LLM to parse user intent"""
        # Integration with AI Assistant's LLM
        prompt = f"""
        Parse the following user request and extract the action and target:
        User: {message}

        Return JSON with 'action' and 'target' fields.
        """
        # Call LLM and parse response
        return {'action': 'deploy', 'target': 'aws'}

    def trigger_deployment(self, target: str) -> Dict[str, Any]:
        """Trigger deployment DAG"""
        dag_id = f'deploy_{target}'
        response = requests.post(
            f'{self.airflow_url}/api/v1/dags/{dag_id}/dagRuns',
            auth=self.auth,
            json={'conf': {'triggered_by': 'chat'}}
        )
        return response.json()

    def get_dag_status(self, dag_run_id: str) -> Dict[str, Any]:
        """Get status of running DAG"""
        response = requests.get(
            f'{self.airflow_url}/api/v1/dags/runs/{dag_run_id}',
            auth=self.auth
        )
        return response.json()

    def list_available_workflows(self) -> list:
        """List all available DAGs"""
        response = requests.get(
            f'{self.airflow_url}/api/v1/dags',
            auth=self.auth
        )
        dags = response.json()['dags']
        return [{'id': d['dag_id'], 'description': d['description']}
                for d in dags if not d['is_paused']]
```

### Chat Command Examples

```bash
# User chat interactions with AI Assistant

User: "Can you ingest the new documentation files?"
AI: "I'll trigger the RAG document ingestion workflow.
     DAG 'rag_document_ingestion' started (run_id: abc123).
     You can monitor progress at: http://localhost:8080/dags/rag_document_ingestion"

User: "What workflows are available?"
AI: "Here are the available workflows:
     1. qubinode_deploy - Deploy Qubinode infrastructure
     2. aws_infrastructure - Provision AWS resources
     3. rag_document_ingestion - Ingest documents into RAG
     4. multi_cloud_sync - Synchronize across clouds
     5. health_check_workflow - System health monitoring

     Which one would you like to run?"

User: "Show me the status of the last ingestion"
AI: "RAG document ingestion (run_id: abc123):
     Status: Running
     Progress: 3/5 tasks complete
     - ✅ scan_for_new_documents (success)
     - ✅ chunk_documents (success)
     - ✅ generate_embeddings (success)
     - 🔄 store_in_vector_db (running)
     - ⏳ notify_ai_assistant (pending)

     Estimated completion: 2 minutes"

User: "Deploy to AWS and GCP simultaneously"
AI: "I'll trigger multi-cloud deployment:
     - aws_infrastructure (run_id: def456) - Started
     - gcp_infrastructure (run_id: ghi789) - Started

     Both workflows are running in parallel.
     I'll notify you when they complete."
```

### Terminal UI Integration

```python
# ai-assistant/src/terminal_workflow_ui.py

from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
import time

class WorkflowTerminalUI:
    """Terminal UI for workflow monitoring"""

    def __init__(self):
        self.console = Console()
        self.airflow = AirflowChatInterface()

    def display_running_workflows(self):
        """Display real-time workflow status in terminal"""
        with Live(self.generate_table(), refresh_per_second=1) as live:
            while True:
                live.update(self.generate_table())
                time.sleep(1)

    def generate_table(self) -> Table:
        """Generate status table"""
        table = Table(title="Active Workflows")
        table.add_column("DAG", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Progress", style="green")
        table.add_column("Duration", style="yellow")

        # Fetch running DAGs from Airflow
        running_dags = self.airflow.get_running_dags()

        for dag in running_dags:
            table.add_row(
                dag['dag_id'],
                dag['state'],
                f"{dag['completed_tasks']}/{dag['total_tasks']}",
                dag['duration']
            )

        return table

    def show_workflow_menu(self):
        """Interactive workflow selection menu"""
        workflows = self.airflow.list_available_workflows()

        self.console.print(Panel("Available Workflows", style="bold blue"))

        for i, workflow in enumerate(workflows, 1):
            self.console.print(f"{i}. {workflow['id']} - {workflow['description']}")

        choice = self.console.input("\n[bold green]Select workflow (number): [/]")
        return workflows[int(choice) - 1]['id']
```

______________________________________________________________________

## Community Contribution Guidelines

### How to Contribute a DAG

1. **Fork the Repository**

   ```bash
   git clone https://github.com/Qubinode/airflow-dags
   cd airflow-dags
   ```

1. **Create Your DAG**

   ```bash
   # Use the template
   cp templates/dag_template.py marketplace/your_category/your_dag.py

   # Edit your DAG
   vim marketplace/your_category/your_dag.py
   ```

1. **Add Documentation**

   ```python
   """
   DAG: Your Workflow Name
   Author: @your_github_username
   Category: infrastructure|data_pipelines|monitoring|ai_workflows
   Tags: tag1, tag2, tag3
   Description: Detailed description of what your DAG does
   Version: 1.0.0
   Dependencies: list, of, required, packages
   License: Apache-2.0

   Usage:
   ------
   1. Install dependencies: pip install -r requirements.txt
   2. Configure variables in Airflow UI
   3. Trigger manually or set schedule_interval

   Configuration:
   --------------
   Required Airflow Variables:
   - your_var_name: Description

   Required Connections:
   - your_conn_id: Connection type and purpose
   """
   ```

1. **Test Your DAG**

   ```bash
   # Validate syntax
   python -m py_compile marketplace/your_category/your_dag.py

   # Test in Airflow
   airflow dags test your_dag_id 2025-11-15
   ```

1. **Submit Pull Request**

   ```bash
   git add marketplace/your_category/your_dag.py
   git commit -m "Add: Your DAG description"
   git push origin your-branch

   # Create PR on GitHub
   ```

### DAG Quality Standards

✅ **Required:**

- Complete docstring with metadata
- Error handling and retries
- Logging for debugging
- Tags for discoverability
- Example configuration

✅ **Recommended:**

- Unit tests
- Integration tests
- Performance considerations
- Security best practices
- Documentation with examples

### Community Support Channels

- **GitHub Discussions**: https://github.com/Qubinode/airflow-dags/discussions
- **Slack Channel**: #airflow-community
- **Monthly Community Calls**: Share workflows and best practices
- **DAG Showcase**: Feature popular community DAGs

### Recognition System

- **Contributor Badge**: For first DAG contribution
- **Power Contributor**: 5+ DAGs contributed
- **Maintainer**: Active community support
- **Featured DAG**: Monthly spotlight on popular workflows

______________________________________________________________________

## RAG Workflow Marketplace

### Pre-built RAG Workflows

```
marketplace/ai_workflows/
├── rag_document_ingestion.py          # Basic document ingestion
├── rag_incremental_update.py          # Incremental updates
├── rag_knowledge_base_sync.py         # Multi-source sync
├── rag_vector_index_optimization.py   # Index optimization
├── rag_model_fine_tuning.py           # Model fine-tuning
├── rag_quality_monitoring.py          # Quality metrics
└── rag_backup_restore.py              # Backup/restore workflows
```

### Easy Import System

```bash
# Import a RAG workflow
./import-rag-workflow.sh rag_document_ingestion

# Configure for your environment
./configure-rag-workflow.sh rag_document_ingestion \
  --doc-path /path/to/docs \
  --vector-db chromadb \
  --embedding-model all-MiniLM-L6-v2

# Test the workflow
airflow dags test rag_document_ingestion 2025-11-15

# Enable in production
airflow dags unpause rag_document_ingestion
```

______________________________________________________________________

## Future Enhancements

### Phase 1: Core Community Features (Q1 2026)

- [ ] GitHub-based DAG marketplace
- [ ] One-click DAG installation
- [ ] Chat interface for workflow triggering
- [ ] Terminal UI for workflow monitoring

### Phase 2: RAG Integration (Q2 2026)

- [ ] Pre-built RAG workflow templates
- [ ] Easy RAG workflow import
- [ ] AI Assistant + Airflow deep integration
- [ ] Natural language workflow creation

### Phase 3: Advanced Community (Q3 2026)

- [ ] DAG rating and review system
- [ ] Automated testing for community DAGs
- [ ] Workflow composition (combine multiple DAGs)
- [ ] Visual DAG builder

### Phase 4: Enterprise Features (Q4 2026)

- [ ] Private DAG repositories
- [ ] Enterprise support packages
- [ ] Advanced RBAC and governance
- [ ] Compliance and audit trails

______________________________________________________________________

## Getting Started

1. **Review the Documentation**

   - [ADR-0036](https://github.com/Qubinode/qubinode_navigator/blob/main/docs/adrs/adr-0036-apache-airflow-workflow-orchestration-integration.md)
   - [Integration Guide](../tutorials/airflow-integration-guide.md)

1. **Set Up Your Environment**

   ```bash
   export ENABLE_AIRFLOW=true
   docker-compose -f docker-compose-airflow.yml up -d
   ```

1. **Create Your First DAG**

   - Use the templates provided
   - Test locally
   - Share with the community

1. **Join the Community**

   - GitHub: https://github.com/Qubinode/airflow-dags
   - Slack: #airflow-community
   - Monthly calls: First Tuesday of each month

______________________________________________________________________

**Let's build an amazing workflow ecosystem together! 🚀**
