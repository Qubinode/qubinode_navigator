---
nav_exclude: true
---

# RAG Tool Quick Reference Card

## Tool Name

**`manage_rag_documents(operation, params)`**

## Location

`/opt/qubinode_navigator/airflow/plugins/qubinode/mcp_server_fastmcp.py`

## Status

✅ **Running & Deployed** (MCP Server Port 8889)

______________________________________________________________________

## Operations at a Glance

| Operation  | Parameters                               | Purpose                             | Output                      |
| ---------- | ---------------------------------------- | ----------------------------------- | --------------------------- |
| `scan`     | `{'doc_dir': '/opt/documents/incoming'}` | Find documents ready for processing | List of files, sizes, count |
| `ingest`   | `{'doc_dir': '/opt/documents/incoming'}` | Start document processing pipeline  | DAG run ID, status          |
| `status`   | None                                     | Check ingestion progress            | DAG info, task pipeline     |
| `list`     | `{'limit': 10}`                          | View processed documents            | Document metadata, chunks   |
| `estimate` | `{'doc_dir': '/opt/documents/incoming'}` | Pre-flight check before ingestion   | Storage needs, timing       |

______________________________________________________________________

## Quick Examples

```python
# Basic scan
manage_rag_documents('scan')

# Estimate requirements
manage_rag_documents('estimate')

# Trigger ingestion
manage_rag_documents('ingest')

# Check progress
manage_rag_documents('status')

# View results (last 5 documents)
manage_rag_documents('list', {'limit': 5})

# Custom directory
manage_rag_documents('scan', {'doc_dir': '/my/docs'})
manage_rag_documents('ingest', {'doc_dir': '/my/docs'})
```

______________________________________________________________________

## Supported File Types

- `.md` - Markdown (chunked by headers)
- `.markdown` - Markdown (alternative extension)
- `.yml` - YAML (entire file as chunk)
- `.yaml` - YAML (alternative extension)
- `.txt` - Plain text (chunked by paragraphs)

______________________________________________________________________

## Workflow Example

```
1. manage_rag_documents('scan')
   ↓
   → Find 3 documents (256 KB)

2. manage_rag_documents('estimate')
   ↓
   → ~180 chunks, 0.41 MB storage, 2 sec processing

3. manage_rag_documents('ingest')
   ↓
   → DAG triggered, run ID: scheduled__2025-11-26...

4. Wait 10-30 seconds...

5. manage_rag_documents('status')
   ↓
   → Pipeline shows 3 tasks complete

6. manage_rag_documents('list')
   ↓
   → 3 documents processed, 25 total chunks
```

______________________________________________________________________

## Features

✅ Read-only operations: `scan`, `status`, `list`, `estimate`
✅ Write operation (requires access): `ingest`
✅ LLM-optimized responses (markdown formatted)
✅ Clear next-step guidance in every response
✅ Comprehensive error messages
✅ Works with custom directories

______________________________________________________________________

## Integration

- **Triggers:** `rag_document_ingestion` Airflow DAG
- **Input:** `/opt/documents/incoming/`
- **Output:** `/opt/documents/processed/metadata.json`
- **Vector DB:** Qdrant, ChromaDB, or FAISS
- **Embedding Model:** all-MiniLM-L6-v2 (384-d)

______________________________________________________________________

## Access Points

| Component  | URL                                                 | Port |
| ---------- | --------------------------------------------------- | ---- |
| MCP Server | `http://localhost:8889/sse`                         | 8889 |
| Airflow UI | `http://localhost:8888/`                            | 8888 |
| RAG DAG    | `http://localhost:8888/dags/rag_document_ingestion` | 8888 |
| PostgreSQL | `localhost:5432`                                    | 5432 |

______________________________________________________________________

## Total MCP Tools

**11 Total:**

- 3 DAG Management
- 5 VM Operations
- 1 Status
- 1 Information
- **1 RAG Operations** ⭐

______________________________________________________________________

## Documentation

- **Full Guide:** `/opt/qubinode_navigator/docs/RAG-TOOL-GUIDE.md`
- **Implementation:** `/opt/qubinode_navigator/RAG-TOOL-IMPLEMENTATION-SUMMARY.md`

______________________________________________________________________

## Troubleshooting Quick Links

- **MCP Server Logs:** `podman logs $(podman ps | grep mcp-server | awk '{print $1}')`
- **Airflow Logs:** `podman logs $(podman ps | grep airflow-scheduler | awk '{print $1}')`
- **Check Tool:** `podman logs ... | grep "Tools: 11"`
- **Verify RAG:** `podman logs ... | grep "RAG: 1"`

______________________________________________________________________

## Key Tip

Always call `manage_rag_documents('estimate')` before `manage_rag_documents('ingest')` to:

- Verify documents are found
- Check storage requirements
- Estimate processing time
- Confirm system readiness

______________________________________________________________________

**Status:** 🟢 Production Ready
**Last Updated:** 2025-11-26
**Tool Version:** 1.0
