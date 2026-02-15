---
title: AI Assistant Container Bind-Mount Fix
parent: Fixes
nav_order: 1
---

# AI Assistant Container Bind-Mount Fix

## Issue Summary

The AI Assistant container was failing to start due to missing bind-mount directories. This document describes the issue, fix, and validation.

## Problem Description

When running `scripts/development/deploy-qubinode.sh`, the AI Assistant container would fail with:

```
Error: statfs /opt/qubinode_navigator/ai-assistant/data: no such file or directory
```

Even after manually creating the directory, the health check would fail, preventing successful deployment.

## Root Causes

1. **Missing Directory**: The `ai-assistant/data` directory was excluded by `.gitignore` and not created before container start
1. **Permission Issues**: The bind-mounted directory needed proper ownership (UID 1001) for the container user
1. **Short Health Check Timeout**: Initial 60-second timeout was insufficient for RAG service initialization
1. **No Troubleshooting Guidance**: Limited information when health checks failed

## Solution

### 1. Automatic Directory Creation

The deployment script now creates required directories before starting the container:

```bash
mkdir -p "${REPO_ROOT}/ai-assistant/data/rag-docs"
mkdir -p "${REPO_ROOT}/ai-assistant/data/vector-db"
```

### 2. Proper Ownership

Sets ownership to match the container user (UID 1001, GID 0):

```bash
chown -R 1001:0 "${REPO_ROOT}/ai-assistant/data"
```

Falls back gracefully if not running as root (SELinux `:z` flag handles permissions).

### 3. Extended Health Check Timeout

Increased from 60 seconds to 120 seconds (60 attempts × 2s) to accommodate:

- Model initialization (if USE_LOCAL_MODEL=true)
- RAG service setup and document loading
- PydanticAI agent context initialization

### 4. Better Error Messages

Added troubleshooting hints when health checks fail:

```
[WARNING] AI Assistant started but health check failed after 120 seconds
[WARNING] Container may still be starting up. Check logs with: podman logs qubinode-ai-assistant
[WARNING] To troubleshoot: curl -v http://localhost:8080/health
```

### 5. Git Repository Structure

- Updated `.gitignore` to exclude data contents but track directory structure
- Added `ai-assistant/data/.gitkeep` to preserve directory in git
- Added patterns for model files and vector databases

## Validation

Run the test suite to validate the fix:

```bash
./tests/test_ai_assistant_bind_mount.sh
```

Expected output:

```
All tests passed! (11/11)

Summary of validated fixes:
  ✓ Data directory structure is properly tracked in git
  ✓ Deploy script creates required directories before mount
  ✓ Deploy script sets correct ownership (UID 1001)
  ✓ Health check timeout increased to 2 minutes
  ✓ SELinux context flag (:z) present in volume mount
  ✓ Troubleshooting hints available for debugging
```

## Manual Verification

If you need to manually verify the fix:

1. **Check directory exists**:

   ```bash
   ls -la ai-assistant/data/
   ```

1. **Verify permissions** (if running container):

   ```bash
   podman exec qubinode-ai-assistant ls -la /app/data
   ```

1. **Check health endpoint**:

   ```bash
   curl -v http://localhost:8080/health
   ```

1. **View container logs**:

   ```bash
   podman logs qubinode-ai-assistant
   ```

## Technical Details

### Container User

The AI Assistant container runs as UID 1001 (non-root user) as defined in the Dockerfile:

```dockerfile
USER 1001
```

### SELinux Context

The `:z` flag in the volume mount ensures proper SELinux labeling:

```bash
-v "${REPO_ROOT}/ai-assistant/data:/app/data:z"
```

This allows the container to read/write even on SELinux-enabled systems (RHEL, CentOS, Rocky Linux).

### Health Check Endpoint

The `/health` endpoint returns:

- **200**: Service is healthy or degraded (operational)
- **503**: Service is unhealthy or not ready

The endpoint checks:

- System resources (CPU, memory, disk)
- RAG service availability
- API responsiveness
- Optional: llama.cpp server (if USE_LOCAL_MODEL=true)

## Related Files

- `scripts/development/deploy-qubinode.sh` - Main deployment script with fixes
- `ai-assistant/data/.gitkeep` - Preserves directory structure in git
- `.gitignore` - Updated patterns for data directory
- `tests/test_ai_assistant_bind_mount.sh` - Validation test suite
- `ai-assistant/Dockerfile` - Container user definition (UID 1001)
- `ai-assistant/src/health_monitor.py` - Health check implementation

## Future Improvements

Potential enhancements for consideration:

1. Add pre-flight validation check for disk space before directory creation
1. Create systemd service for automatic container restart
1. Add metrics endpoint for health monitoring
1. Implement health check retry with exponential backoff
1. Add container logs streaming during deployment

## References

- ADR-0027: CPU-Based AI Deployment Assistant Architecture
- ADR-0063: PydanticAI Multi-Agent Orchestration
- Issue: AI Assistant container fails health check due to bind-mount permissions
