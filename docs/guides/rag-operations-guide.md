---
title: RAG Operations Guide
parent: Guides
nav_order: 1
---

# RAG Operations Guide

**ADR-0049: Multi-Agent LLM Memory Architecture**

This guide covers the RAG (Retrieval-Augmented Generation) system operations for Qubinode Navigator.

## Overview

The RAG system provides:

- **Document Storage**: ADRs, DAG examples, provider docs
- **Semantic Search**: Find relevant documents by meaning, not just keywords
- **Troubleshooting Memory**: Learn from past solutions
- **Agent Decisions**: Track decision history for learning

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                        RAG Store                                │
├────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ Embedding   │  │  PgVector   │  │    PostgreSQL           │ │
│  │ Service     │─▶│  Extension  │─▶│    Tables               │ │
│  │ (MiniLM)    │  │  (vector)   │  │                         │ │
│  └─────────────┘  └─────────────┘  │  - rag_documents        │ │
│                                     │  - troubleshooting_     │ │
│                                     │    attempts             │ │
│                                     │  - agent_decisions      │ │
│                                     │  - airflow_providers    │ │
│                                     └─────────────────────────┘ │
└────────────────────────────────────────────────────────────────┘
```

## Database Schema

### rag_documents

Stores document embeddings for semantic search.

| Column       | Type        | Description                  |
| ------------ | ----------- | ---------------------------- |
| id           | UUID        | Primary key                  |
| content      | TEXT        | Document content             |
| content_hash | VARCHAR(64) | SHA256 for deduplication     |
| embedding    | vector(384) | MiniLM embedding             |
| doc_type     | VARCHAR(50) | adr, dag, provider_doc, etc. |
| source_path  | TEXT        | File path or URL             |
| metadata     | JSONB       | Additional metadata          |
| created_at   | TIMESTAMP   | Creation time                |

### troubleshooting_attempts

Records troubleshooting history for learning.

| Column             | Type        | Description               |
| ------------------ | ----------- | ------------------------- |
| id                 | UUID        | Primary key               |
| session_id         | UUID        | Session identifier        |
| task_description   | TEXT        | What was attempted        |
| error_message      | TEXT        | Error encountered         |
| attempted_solution | TEXT        | Solution tried            |
| result             | VARCHAR(20) | success, failed, partial  |
| embedding          | vector(384) | For similarity search     |
| confidence_score   | FLOAT       | Confidence when attempted |
| agent              | VARCHAR(50) | Which agent made decision |

### agent_decisions

Logs all agent decisions for auditing.

| Column        | Type        | Description                      |
| ------------- | ----------- | -------------------------------- |
| id            | UUID        | Primary key                      |
| agent         | VARCHAR(50) | manager, developer, calling_llm  |
| decision_type | VARCHAR(50) | task_execution, escalation, etc. |
| decision      | TEXT        | What was decided                 |
| reasoning     | TEXT        | Why it was decided               |
| confidence    | FLOAT       | Confidence score                 |
| outcome       | VARCHAR(20) | success, failed, pending         |

## Operations

### Document Ingestion

**Via MCP Tool:**

```
ingest_to_rag(
  content="# My Document\n\nContent here...",
  doc_type="guide",
  source="/path/to/file.md",
  metadata={"author": "team", "version": "1.0"}
)
```

**Via Python:**

```python
from qubinode.rag_store import get_rag_store

store = get_rag_store()
store.ingest_document(
    content="Document content",
    doc_type="adr",
    source_path="/docs/adrs/adr-0001.md",
    metadata={"title": "ADR-0001"}
)
```

### Document Search

**Via MCP Tool:**

```
query_rag(
  query="How do I deploy FreeIPA?",
  doc_types=["adr", "dag", "guide"],
  limit=5,
  threshold=0.7
)
```

**Via Python:**

```python
results = store.search_documents(
    query="FreeIPA deployment",
    doc_types=["adr", "dag"],
    limit=5,
    threshold=0.7
)

for doc in results:
    print(f"Score: {doc['similarity']:.2f}")
    print(f"Type: {doc['doc_type']}")
    print(f"Content: {doc['content'][:200]}...")
```

### Troubleshooting History

**Log an attempt:**

```
log_troubleshooting_attempt(
  task="Deploy FreeIPA server",
  solution="Added entry to /etc/hosts for DNS resolution",
  result="success",
  error_message="DNS lookup failed for ipa.example.com",
  component="freeipa"
)
```

**Search similar errors:**

```
get_troubleshooting_history(
  error_pattern="DNS",
  component="freeipa",
  only_successful=True
)
```

### Statistics

**Via MCP Tool:**

```
get_rag_stats()
```

**Via SQL:**

```sql
-- Document counts by type
SELECT doc_type, COUNT(*)
FROM rag_documents
GROUP BY doc_type;

-- Troubleshooting success rate
SELECT result, COUNT(*)
FROM troubleshooting_attempts
GROUP BY result;

-- Recent agent decisions
SELECT agent, decision_type, confidence, created_at
FROM agent_decisions
ORDER BY created_at DESC
LIMIT 10;
```

## Embedding Service

### Configuration

| Variable               | Default                                | Description         |
| ---------------------- | -------------------------------------- | ------------------- |
| `EMBEDDING_PROVIDER`   | local                                  | local or openai     |
| `EMBEDDING_MODEL`      | sentence-transformers/all-MiniLM-L6-v2 | Model name          |
| `EMBEDDING_DIMENSIONS` | 384                                    | Vector dimensions   |
| `OPENAI_API_KEY`       | -                                      | Required for OpenAI |

### Local Model (Default)

Uses `sentence-transformers/all-MiniLM-L6-v2`:

- 384 dimensions
- Works offline (air-gapped)
- Good balance of speed and quality
- ~80MB model size

### OpenAI Model (Optional)

Uses `text-embedding-ada-002`:

- 1536 dimensions
- Requires API key and internet
- Higher quality but external dependency

**To switch:**

```bash
export EMBEDDING_PROVIDER=openai
export EMBEDDING_MODEL=text-embedding-ada-002
export EMBEDDING_DIMENSIONS=1536
export OPENAI_API_KEY=your-key-here
```

## Bootstrap DAG

The `rag_bootstrap` DAG initializes the knowledge base:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  ingest_adrs    │     │ ingest_dags     │     │ingest_providers │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   verify_rag_health     │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ generate_lineage_facets │
                    └─────────────────────────┘
```

**Trigger:**

```bash
airflow dags trigger rag_bootstrap
```

**Tasks:**

1. `ingest_adrs` - Ingests docs/adrs/\*.md
1. `ingest_dag_examples` - Ingests existing DAG files
1. `ingest_provider_docs` - Ingests provider documentation
1. `ingest_guides` - Ingests troubleshooting guides
1. `verify_rag_health` - Verifies system health
1. `generate_lineage_facets` - Generates OpenLineage facets

## Maintenance

### Rebuilding Index

If similarity search is slow:

```sql
-- Drop and recreate IVFFlat index
DROP INDEX IF EXISTS idx_rag_documents_embedding;

CREATE INDEX idx_rag_documents_embedding
    ON rag_documents USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

### Cleaning Duplicates

```sql
-- Remove duplicate documents by content hash
DELETE FROM rag_documents a
USING rag_documents b
WHERE a.id > b.id
AND a.content_hash = b.content_hash;
```

### Updating Embeddings

If you change embedding models:

```python
from qubinode.rag_store import get_rag_store
from qubinode.embedding_service import get_embedding_service

store = get_rag_store()
embedding_service = get_embedding_service()

# Re-embed all documents
with store._get_connection() as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT id, content FROM rag_documents")
        for row in cur.fetchall():
            doc_id, content = row
            new_embedding = embedding_service.embed(content)
            cur.execute(
                "UPDATE rag_documents SET embedding = %s WHERE id = %s",
                (new_embedding, doc_id)
            )
    conn.commit()
```

## Performance Tuning

### Index Lists

The IVFFlat index `lists` parameter affects performance:

| Documents        | Recommended Lists |
| ---------------- | ----------------- |
| < 1,000          | 50                |
| 1,000 - 10,000   | 100               |
| 10,000 - 100,000 | 200               |
| > 100,000        | 400+              |

### Query Optimization

```sql
-- Set probes for accuracy vs speed tradeoff
SET ivfflat.probes = 10;  -- Higher = more accurate, slower
```

### Batch Operations

For bulk ingestion:

```python
# Use batch embedding
texts = ["doc1", "doc2", "doc3", ...]
embeddings = embedding_service.embed_batch(texts, batch_size=32)
```

## Troubleshooting

### "pgvector extension not found"

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Or check Docker image:

```bash
docker exec airflow-postgres-1 psql -U airflow -c "SELECT * FROM pg_extension WHERE extname = 'vector'"
```

### "Embedding dimension mismatch"

Ensure `EMBEDDING_DIMENSIONS` matches your model:

- MiniLM-L6: 384
- ada-002: 1536

### Slow Queries

1. Check index exists:

   ```sql
   SELECT indexname FROM pg_indexes WHERE tablename = 'rag_documents';
   ```

1. Increase probes:

   ```sql
   SET ivfflat.probes = 20;
   ```

1. Rebuild index with more lists (see Rebuilding Index)

### Empty Results

1. Check document count:

   ```sql
   SELECT COUNT(*) FROM rag_documents;
   ```

1. Lower threshold:

   ```python
   results = store.search_documents(query, threshold=0.3)
   ```

1. Run bootstrap:

   ```bash
   airflow dags trigger rag_bootstrap
   ```

## Related Documentation

- [Multi-Agent LLM Guide](multi-agent-llm-guide.md)
- [ADR-0049: Multi-Agent LLM Memory Architecture](../adrs/adr-0049-multi-agent-llm-memory-architecture.md)
