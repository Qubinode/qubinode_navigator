---
nav_exclude: true
---

# RAG Operations Tool - Implementation Guide

## Overview

A new **11th MCP tool** has been implemented: `manage_rag_documents()` for Retrieval-Augmented Generation (RAG) document ingestion and management. This tool enables LLMs to control the full document lifecycle without requiring separate API calls.

## Tool Status

✅ **Implemented and Deployed**

- Tool Count: **11 total** (DAGs: 3, VMs: 5, Status: 1, Info: 1, **RAG: 1**)
- MCP Server: Running on port 8889
- FastMCP Version: 2.13.1
- Transport: Server-Sent Events (SSE)

## RAG Tool Operations

### 1. `scan` - Discover Documents

Scan `/opt/documents/incoming/` for documents ready for ingestion.

```python
manage_rag_documents('scan')
```

**Returns:**

- List of discovered files with metadata
- File types: `.md`, `.markdown`, `.yml`, `.yaml`, `.txt`
- Total size calculation
- Document count

**Example Response:**

```
# RAG Document Scan

**Directory:** `/opt/documents/incoming`
**Timestamp:** 2025-11-26T19:45:00.000Z

## Found 3 document(s)

**Total Size:** 256.50 KB

| File | Type | Size (KB) |
|------|------|----------|
| architecture.md | .md | 128.75 |
| config.yml | .yml | 64.25 |
| readme.txt | .txt | 63.50 |

**Next Step:** Call `manage_rag_documents('ingest')` to process these documents
```

### 2. `ingest` - Trigger Ingestion Pipeline

Start the `rag_document_ingestion` DAG to process discovered documents.

```python
manage_rag_documents('ingest')
```

**Parameters:**

- Optional `doc_dir`: Custom directory (default: `/opt/documents/incoming`)

```python
manage_rag_documents('ingest', {'doc_dir': '/custom/path'})
```

**Returns:**

- DAG run ID
- Status confirmation
- Next steps for monitoring

**Example Response:**

```
# RAG Document Ingestion

✅ **Ingestion triggered successfully**

**DAG Run ID:** `scheduled__2025-11-26T19:45:30.123456+00:00`
**Source Directory:** `/opt/documents/incoming`
**Status:** Queued
**Timestamp:** 2025-11-26T19:45:30.123Z

**Next Steps:**
1. Wait 10-30 seconds for tasks to execute
2. Call `manage_rag_documents('status')` to check progress
3. View detailed logs in Airflow UI: http://localhost:8888/dags/rag_document_ingestion
```

**Behind the Scenes:**

- Triggers `rag_document_ingestion` DAG
- `scan_documents` task: Discovers files
- `chunk_documents` task: Splits into chunks
- `store_metadata` task: Records chunk metadata

### 3. `status` - Check Ingestion Progress

Get the current status of the RAG ingestion pipeline.

```python
manage_rag_documents('status')
```

**Returns:**

- DAG information
- Task pipeline overview
- Recent run details
- Link to Airflow UI for detailed logs

**Example Response:**

```
# RAG Ingestion Status

**Timestamp:** 2025-11-26T19:46:00.000Z

## DAG: rag_document_ingestion

**Schedule:** Manual
**Tasks:** 3 total

### Task Pipeline
- `scan_documents`: PythonOperator
- `chunk_documents`: PythonOperator
- `store_metadata`: PythonOperator

### Recent Runs
(Check Airflow UI for detailed task logs: http://localhost:8888/dags/rag_document_ingestion)
```

### 4. `list` - Show Processed Documents

List documents that have been successfully processed and ingested.

```python
manage_rag_documents('list')
manage_rag_documents('list', {'limit': 10})
```

**Parameters:**

- `limit`: Maximum results to return (default: 10)

**Returns:**

- Processed document metadata
- Chunk counts
- Processing timestamps
- File paths

**Example Response:**

```
# Processed RAG Documents

**Limit:** 10 results
**Timestamp:** 2025-11-26T19:47:00.000Z

## 3 document(s) processed

### 1. architecture.md
- **Path:** `/opt/documents/incoming/architecture.md`
- **Type:** .md
- **Chunks:** 12
- **Processed:** 2025-11-26T19:46:15.000Z

### 2. config.yml
- **Path:** `/opt/documents/incoming/config.yml`
- **Type:** .yml
- **Chunks:** 5
- **Processed:** 2025-11-26T19:46:22.000Z

### 3. readme.txt
- **Path:** `/opt/documents/incoming/readme.txt`
- **Type:** .txt
- **Chunks:** 8
- **Processed:** 2025-11-26T19:46:30.000Z
```

### 5. `estimate` - Calculate Storage Requirements

Estimate chunking requirements and storage before ingestion.

```python
manage_rag_documents('estimate')
manage_rag_documents('estimate', {'doc_dir': '/custom/path'})
```

**Returns:**

- Document statistics (count, size, words)
- Chunking estimates (chunks, embedding dimension)
- Storage requirements (vector DB size)
- Quality metrics
- Processing time estimate

**Example Response:**

```
# RAG Chunk Estimation

**Source Directory:** `/opt/documents/incoming`
**Timestamp:** 2025-11-26T19:48:00.000Z

## Document Statistics
- **Total Documents:** 3
- **Total Content Size:** 256.50 KB
- **Total Words:** 45,200

## Chunking Estimate
- **Average Chunk Size:** ~250 words
- **Estimated Chunks:** ~180
- **Embedding Dimension:** 384-d

## Storage Requirements
- **Vector DB Size (estimated):** ~0.27 MB
- **Including Metadata:** ~0.41 MB

## Quality Metrics
- **Documents Ready:** ✅ Yes (>0 documents found)
- **Sufficient Content:** ✅ Yes
- **Processing Time Est:** ~2 seconds

**Next Step:** Call `manage_rag_documents('ingest')` to process documents
```

## Implementation Details

### Helper Functions

The tool includes five specialized helper functions:

1. **`_rag_scan_documents(doc_dir)`**

   - Recursively scans directory
   - Filters by supported file types
   - Calculates file sizes and statistics

1. **`_rag_trigger_ingestion(doc_dir)`**

   - Calls Airflow `trigger_dag_api()`
   - Passes configuration to DAG
   - Returns DAG run ID and status

1. **`_rag_ingestion_status()`**

   - Queries DAG from DagBag
   - Lists task pipeline
   - Provides links to Airflow UI

1. **`_rag_list_processed(limit)`**

   - Reads metadata from `/opt/documents/processed/metadata.json`
   - Parses and displays document information
   - Limits results as specified

1. **`_rag_estimate_chunks(doc_dir)`**

   - Scans documents and counts words
   - Calculates chunks (250 words per chunk)
   - Estimates storage (384-dim embeddings * 4 bytes)
   - Provides quality and timing estimates

### Feature Highlights

- **Read-only compatible**: `scan`, `status`, `list`, `estimate` work in read-only mode
- **Write access required**: Only `ingest` operation requires write access
- **Error handling**: Comprehensive error messages with troubleshooting guidance
- **Stateless operations**: Each call is independent, no session state
- **Beginner-friendly**: Clear next-steps guidance in every response
- **LLM-optimized**: Structured responses with clear formatting

## Integration Points

### Airflow DAG Integration

- Triggers: `rag_document_ingestion` DAG
- Input: Documents in `/opt/documents/incoming/`
- Output: Metadata stored in `/opt/documents/processed/`
- Processing: 3-task pipeline (scan → chunk → store)

### Vector Database

- Supported backends: Qdrant (recommended), ChromaDB, FAISS
- Embedding model: `all-MiniLM-L6-v2` (384-dimensional)
- Storage: `/opt/documents/processed/` and vector DB

### Directory Structure

```
/opt/documents/
├── incoming/           # Documents awaiting ingestion
│   ├── *.md
│   ├── *.yml
│   └── *.txt
└── processed/          # Processed document metadata
    └── metadata.json   # Chunk information
```

## Usage Examples

### Example 1: Full Ingestion Workflow

```python
# 1. Discover documents
result = await manage_rag_documents('scan')
# Output: Found 3 documents (256 KB)

# 2. Estimate requirements
result = await manage_rag_documents('estimate')
# Output: ~180 chunks, 0.41 MB storage, 2 sec processing

# 3. Trigger ingestion
result = await manage_rag_documents('ingest')
# Output: DAG run ID scheduled

# 4. Check status
result = await manage_rag_documents('status')
# Output: Task pipeline ready

# 5. Wait and verify
time.sleep(30)  # Let processing complete
result = await manage_rag_documents('list')
# Output: 3 documents processed, 25 chunks total
```

### Example 2: Check Custom Directory

```python
# Estimate documents in custom location
result = await manage_rag_documents('estimate',
    {'doc_dir': '/home/user/my-docs'})

# Ingest from custom directory
result = await manage_rag_documents('ingest',
    {'doc_dir': '/home/user/my-docs'})
```

### Example 3: List Recent Ingestions

```python
# Get last 5 processed documents
result = await manage_rag_documents('list', {'limit': 5})
```

## Troubleshooting

### Documents not found in scan

**Symptoms:** `No supported documents found` message

**Solutions:**

1. Verify directory exists: `ls -la /opt/documents/incoming/`
1. Check file permissions: `stat /opt/documents/incoming/`
1. Ensure files have supported extensions: `.md`, `.yml`, `.yaml`, `.txt`
1. Files must be readable by Airflow container user

### Ingestion fails

**Symptoms:** DAG run status is FAILED or SKIPPED

**Solutions:**

1. Check Airflow UI: http://localhost:8888/dags/rag_document_ingestion
1. Review task logs for specific errors
1. Verify PostgreSQL database is healthy: `podman ps | grep postgres`
1. Ensure scheduler is running: `podman ps | grep scheduler`

### Ingest operation blocked (read-only mode)

**Symptoms:** "operation requires write access but read-only mode is enabled"

**Solutions:**

1. Disable read-only mode: `export AIRFLOW_MCP_TOOLS_READ_ONLY=false`
1. Restart MCP server with new setting
1. Other operations (scan, status, list, estimate) still work in read-only mode

### Empty list of processed documents

**Symptoms:** `No processed documents yet` message

**Solutions:**

1. Ensure ingestion has completed: `manage_rag_documents('status')`
1. Wait 30+ seconds after triggering ingest before listing
1. Check metadata file exists: `ls -la /opt/documents/processed/metadata.json`
1. Review Airflow UI for DAG execution status

## Monitoring

### Airflow UI

- **DAG:** http://localhost:8888/dags/rag_document_ingestion
- **Task Instance Logs:** View detailed task execution output
- **XCom Pull:** See discovered documents and chunks passed between tasks

### MCP Server Logs

```bash
podman logs $(podman ps | grep mcp-server | awk '{print $1}') | grep -E "manage_rag|RAG|ingestion"
```

### System Resources

```bash
# Check disk space for documents
du -sh /opt/documents/

# Monitor vector DB size
du -sh /opt/documents/processed/

# Check PostgreSQL connection
podman exec airflow_postgres_1 psql -U airflow -d airflow -c "SELECT COUNT(*) FROM dag_run WHERE dag_id='rag_document_ingestion';"
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│ LLM / Claude Desktop                                    │
│ (calls MCP tools)                                       │
└────────────────┬────────────────────────────────────────┘
                 │
                 │ MCP Protocol (HTTP/SSE)
                 │
┌────────────────▼────────────────────────────────────────┐
│ FastMCP Server (Port 8889)                              │
│ ┌──────────────────────────────────────────────────┐   │
│ │ manage_rag_documents(operation, params)          │   │
│ │ ├─ scan: _rag_scan_documents()                   │   │
│ │ ├─ ingest: _rag_trigger_ingestion()              │   │
│ │ ├─ status: _rag_ingestion_status()               │   │
│ │ ├─ list: _rag_list_processed()                   │   │
│ │ └─ estimate: _rag_estimate_chunks()              │   │
│ └──────────────────────────────────────────────────┘   │
└────────────────┬────────────────────────────────────────┘
                 │
    ┌────────────┴────────────┐
    │                         │
    │                         │
    ▼                         ▼
┌─────────────────┐   ┌──────────────────────────┐
│ Airflow DAG     │   │ File System              │
│ (Port 8888)     │   │                          │
│ - scheduler     │   │ /opt/documents/          │
│ - webserver     │   │  ├─ incoming/ (read)     │
│ - postgresql    │   │  └─ processed/ (write)   │
│ - mcp-server    │   │                          │
└─────────────────┘   └──────────────────────────┘
      │
      │ trigger_dag()
      │
      ▼
┌─────────────────────────────────────┐
│ rag_document_ingestion DAG          │
│ ├─ scan_documents                   │
│ ├─ chunk_documents                  │
│ └─ store_metadata                   │
└─────────────────────────────────────┘
      │
      ▼
┌─────────────────────────────────────┐
│ Vector Database                     │
│ (Qdrant / ChromaDB / FAISS)        │
│                                     │
│ Documents → Chunks → Embeddings    │
└─────────────────────────────────────┘
```

## Next Steps

### For LLM Integration

1. Use `manage_rag_documents('scan')` to discover available documents
1. Use `manage_rag_documents('estimate')` before large ingestions
1. Use `manage_rag_documents('ingest')` to trigger processing
1. Use `manage_rag_documents('list')` to verify completion

### For Vector Database Expansion

1. Enhance `_rag_store_metadata()` in Airflow DAG for actual embedding generation
1. Implement vector search interface (query_documents MCP tool)
1. Add bidirectional learning between Airflow and RAG system

### For Production Hardening

1. Add retry logic for failed ingestions
1. Implement document validation (quality scoring)
1. Add batch processing for large document sets
1. Monitor vector DB growth and performance

## Configuration

### Environment Variables

```bash
# Enable MCP server
export AIRFLOW_MCP_ENABLED=true

# Set MCP port
export AIRFLOW_MCP_PORT=8889

# Enable/disable write access
export AIRFLOW_MCP_TOOLS_READ_ONLY=false

# Set document directory
export RAG_DOC_DIR=/opt/documents/incoming
```

### Airflow Configuration

```yaml
# airflow/config/airflow.env
AIRFLOW_MCP_ENABLED=true
AIRFLOW_MCP_PORT=8889
AIRFLOW__CORE__EXECUTOR=LocalExecutor
AIRFLOW__CORE__DAGS_FOLDER=/opt/airflow/dags
```

## Version Information

- **Tool Version:** 1.0
- **MCP Spec:** Compatible with Model Context Protocol
- **FastMCP Version:** 2.13.1+
- **Airflow Version:** 2.10.4+
- **Python Version:** 3.12+

## Support & Debugging

### Enable Debug Logging

```bash
export AIRFLOW__LOGGING__LOGGING_LEVEL=DEBUG
podman-compose restart
podman logs $(podman ps | grep mcp-server | awk '{print $1}') -f
```

### Check Tool Registration

```bash
podman logs $(podman ps | grep mcp-server | awk '{print $1}') 2>&1 | grep "Tools:"
```

### Verify MCP Server

```bash
curl -s http://localhost:8889/sse
# Should respond quickly (may timeout, which is normal for SSE)
```

______________________________________________________________________

**Status:** ✅ Production Ready
**Last Updated:** 2025-11-26
**Tool Count:** 11 (DAGs: 3, VMs: 5, Status: 1, Info: 1, **RAG: 1**)
