---
title: Ingest New Docs into RAG
parent: How to
nav_order: 3
---

# How To: Ingest New Documents into RAG

> **Documentation status**
>
> - Validation: `IN PROGRESS` – Simplified recipe based on the RAG ingestion DAG.
> - Last reviewed: 2025-11-21
> - Community: If you refine this workflow, please update it via [Contributing to docs](./contribute.md).

This is a short recipe for ingesting new documents into the Qubinode RAG system once Airflow and the AI Assistant are already running.

## Prerequisites

- Youve completed:
  - [Getting Started with Apache Airflow for Qubinode Navigator](../tutorials/airflow-getting-started.md)
  - [RAG Document Ingestion Tutorial](../tutorials/rag-document-ingestion.md)
- The `rag_document_ingestion` DAG (or similar) is available in your Airflow instance.

## Steps

### 1. Add or Update Documents

1. Copy new or updated docs into your RAG ingress directory, for example:

```bash
sudo mkdir -p /opt/documents/incoming
sudo chown $(whoami) /opt/documents/incoming

cp ~/my-updated-docs/*.md /opt/documents/incoming/
```

2. Ensure file permissions allow the Airflow container to read them.

### 2. Trigger the RAG Ingestion DAG

1. Open the Airflow UI.
1. Find the RAG ingestion DAG (e.g., `rag_document_ingestion`).
1. Unpause it if needed.
1. Trigger a DAG run:
   - Optionally provide parameters if your DAG supports custom paths.

### 3. Confirm Ingestion Succeeded

- Check DAG run status in Airflow.
- Review task logs for:
  - Number of new documents found.
  - Number of chunks and embeddings created.

### 4. Test with the AI Assistant

- Ask questions that rely on the new/updated docs.
- If answers are missing or outdated, check:
  - The document path used in the DAG.
  - Whether the ingestion DAG completed successfully.
  - Any errors reported in logs.

______________________________________________________________________

If you frequently ingest new docs, consider scheduling the ingestion DAG or adding a dedicated incremental-update DAG and documenting it here.
