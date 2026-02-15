---
title: RAG Document Ingestion
parent: Tutorials
nav_order: 4
---

# RAG Document Ingestion Tutorial

> **Documentation status**
>
> - Validation: `IN PROGRESS` – Based on the `rag_document_ingestion` DAG and current RAG integration.
> - Last reviewed: 2025-11-21
> - Community: If you successfully ingest your own docs (or hit issues), please update this tutorial via [Contributing to docs](../how-to/contribute.md).

This tutorial shows how to ingest your own documentation into the **RAG (Retrieval‑Augmented Generation) system** used by the Qubinode Navigator AI Assistant.

You will:

1. Prepare a directory of documents.
1. Configure the RAG ingestion path.
1. Run the `rag_document_ingestion` DAG in Airflow.
1. Verify that new content is available to the AI Assistant.

______________________________________________________________________

## 1. Prerequisites

Before you begin, you should have:

- Qubinode Navigator + Airflow deployed, for example via:
  - [Getting Started with Apache Airflow for Qubinode Navigator](./airflow-getting-started.md)
- Access to the **Airflow UI** (via nginx, as configured in `deploy-qubinode-with-airflow.sh`).
- The RAG integration enabled and the AI Assistant running (see:
  - [Airflow ↔ RAG Bidirectional Learning](../airflow-rag-bidirectional-learning.md)
  - [Airflow Community Ecosystem](../airflow-community-ecosystem.md)

______________________________________________________________________

## 2. Prepare Your Documents

Decide which documents you want the AI Assistant to be able to search.

Typical formats:

- Markdown (`.md`)
- Text (`.txt`)
- Possibly other formats, depending on your RAG ingestion pipeline configuration.

1. On the host where Airflow is running, create or use a directory for incoming docs, for example:

```bash
sudo mkdir -p /opt/documents/incoming
sudo chown $(whoami) /opt/documents/incoming
```

2. Copy or sync your docs into this directory, for example:

```bash
cp -r ~/my-docs/*.md /opt/documents/incoming/
```

The example `rag_document_ingestion` DAG in `airflow-community-ecosystem.md` assumes a directory like `/opt/documents/incoming`.

______________________________________________________________________

## 3. Review the `rag_document_ingestion` DAG

In the repository, the RAG ingestion DAG is described in:

- [Airflow Community Ecosystem](../airflow-community-ecosystem.md) – section **"RAG Workflow Integration"** and the `rag_document_ingestion` example.

A simplified version of the DAG flow is:

1. **Scan for new documents** in the incoming directory.
1. **Chunk documents** into smaller pieces.
1. **Generate embeddings** for each chunk.
1. **Store embeddings** and text in the vector database.
1. **Notify the AI Assistant** that new chunks are available.

Ensure the paths in the DAG match your actual document directory.

______________________________________________________________________

## 4. Run the Ingestion DAG from Airflow UI

1. Open the **Airflow UI** in your browser (via nginx):

   - `http://YOUR_HOST_IP/`

1. In the DAGs list, locate:

   - `rag_document_ingestion` (or your equivalent RAG ingestion DAG).

1. If the DAG is paused, unpause it.

1. Trigger a manual run:

   - Click the **Play** button.
   - Optionally supply configuration via the run dialog if the DAG expects parameters (e.g., custom document path).

1. Monitor the run:

   - View the **Graph** or **Tree** for task statuses.
   - Inspect task logs for:
     - Number of documents found.
     - Number of chunks generated.
     - Any errors in embedding generation or vector DB writes.

______________________________________________________________________

## 5. Verify RAG Has the New Documents

After a successful DAG run:

1. Use the AI Assistant (chat interface) and ask questions that should be answerable from your new docs.
1. If the RAG system exposes any diagnostic endpoints or CLI tools, use them to:
   - List collections.
   - Confirm new vectors have been added.

If answers dont reflect new content:

- Re-check:
  - The document directory path in the DAG.
  - File permissions for the Airflow container.
  - Any filtering logic in the ingestion code.

______________________________________________________________________

## 6. Keeping RAG Updated

You can keep RAG in sync by:

- Scheduling the `rag_document_ingestion` DAG to run periodically.
- Using a separate DAG for incremental updates (see examples in `airflow-community-ecosystem.md`).

For more advanced RAG workflows (incremental updates, quality monitoring, etc.), see:

- [Airflow Community Ecosystem](../airflow-community-ecosystem.md)
- [Airflow ↔ RAG Bidirectional Learning](../airflow-rag-bidirectional-learning.md)

______________________________________________________________________

## 7. Contribute Improvements

If you:

- Add support for new file types,
- Improve chunking/embedding performance, or
- Create additional RAG workflows,

please consider:

- Adding notes or examples to this tutorial.
- Contributing new DAG examples to the repository.
