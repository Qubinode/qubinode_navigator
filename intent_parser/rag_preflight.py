"""
RAG pre-flight checks with auto-fix for orchestrator requests.

Validates that the RAG document store has documents loaded before the
orchestrator processes a request. After container restart, RAG has 0
documents, causing Developer Agent confidence to drop below 0.6 and
every task to escalate. This module detects the empty state and
auto-fixes by triggering /orchestrator/context/reload.

Results are cached to avoid repeated checks on consecutive requests.
Never blocks — can_proceed=True always.
"""

import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional

import httpx

from .ssh_preflight import CheckStatus, PreflightCheck, PreflightResult

logger = logging.getLogger("intent-parser.rag-preflight")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def _get_config() -> Dict[str, any]:
    return {
        "ai_assistant_url": os.getenv("AI_ASSISTANT_URL", "http://localhost:8080"),
        "qubinode_root": os.getenv("QUBINODE_ROOT", "/opt/qubinode_navigator"),
        "rag_data_dir": os.getenv("RAG_DATA_DIR", "/app/data"),
        "cache_ttl": int(os.getenv("RAG_PREFLIGHT_CACHE_TTL", "300")),
    }


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

_cache: Dict[str, tuple] = {}  # {"rag": (timestamp, PreflightResult)}


def clear_cache() -> None:
    """Clear the preflight cache (useful for testing)."""
    _cache.clear()


def _get_cached(ttl: int) -> Optional[PreflightResult]:
    entry = _cache.get("rag")
    if entry is None:
        return None
    ts, result = entry
    if time.time() - ts > ttl:
        del _cache["rag"]
        return None
    return result


def _set_cached(result: PreflightResult) -> None:
    _cache["rag"] = (time.time(), result)


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def _check_adr_source_files(qubinode_root: str) -> PreflightCheck:
    """Check if ADR source files exist on the filesystem."""
    adr_dir = Path(qubinode_root) / "docs" / "adrs"

    if not adr_dir.is_dir():
        return PreflightCheck(
            name="adr_source_files",
            status=CheckStatus.WARNING,
            message=f"ADR directory not found: {adr_dir}",
        )

    adr_files = list(adr_dir.glob("adr-*.md"))
    if not adr_files:
        return PreflightCheck(
            name="adr_source_files",
            status=CheckStatus.WARNING,
            message=f"ADR directory exists but contains no adr-*.md files: {adr_dir}",
        )

    return PreflightCheck(
        name="adr_source_files",
        status=CheckStatus.OK,
        message=f"Found {len(adr_files)} ADR files in {adr_dir}",
    )


def _check_chunks_file(rag_data_dir: str) -> PreflightCheck:
    """Check if the RAG document chunks file exists and is non-trivial."""
    chunks_path = Path(rag_data_dir) / "rag-docs" / "document_chunks.json"

    if not chunks_path.is_file():
        return PreflightCheck(
            name="chunks_file",
            status=CheckStatus.WARNING,
            message=f"Chunks file not found: {chunks_path}",
        )

    size = chunks_path.stat().st_size
    if size < 100:  # Trivially small (empty JSON array or similar)
        return PreflightCheck(
            name="chunks_file",
            status=CheckStatus.WARNING,
            message=f"Chunks file is trivially small ({size} bytes): {chunks_path}",
        )

    return PreflightCheck(
        name="chunks_file",
        status=CheckStatus.OK,
        message=f"Chunks file exists ({size} bytes)",
    )


async def _check_rag_document_count(
    client: httpx.AsyncClient, ai_assistant_url: str
) -> tuple:
    """Check the health endpoint for document count.

    Returns (PreflightCheck, needs_reload: bool).
    """
    try:
        resp = await client.get(f"{ai_assistant_url}/health")
    except Exception as exc:
        return PreflightCheck(
            name="rag_document_count",
            status=CheckStatus.WARNING,
            message=f"Cannot reach AI Assistant health endpoint: {exc}",
        ), False

    if resp.status_code != 200:
        return PreflightCheck(
            name="rag_document_count",
            status=CheckStatus.WARNING,
            message=f"Health endpoint returned HTTP {resp.status_code}",
        ), False

    try:
        data = resp.json()
    except Exception:
        return PreflightCheck(
            name="rag_document_count",
            status=CheckStatus.WARNING,
            message="Health endpoint returned non-JSON response",
        ), False

    # Navigate the health response to find document count
    # The structure may vary; check common locations
    doc_count = 0
    docs_loaded = False

    # Check nested structures
    services = data.get("services", {})
    rag_status = services.get("rag", {})
    if isinstance(rag_status, dict):
        doc_count = rag_status.get("document_count", 0)
        docs_loaded = rag_status.get("documents_loaded", False)

    # Also check top-level
    if not doc_count:
        doc_count = data.get("document_count", 0)
    if not docs_loaded:
        docs_loaded = data.get("documents_loaded", False)

    if doc_count == 0 and not docs_loaded:
        return PreflightCheck(
            name="rag_document_count",
            status=CheckStatus.WARNING,
            message=f"RAG has 0 documents loaded (documents_loaded={docs_loaded})",
        ), True

    return PreflightCheck(
        name="rag_document_count",
        status=CheckStatus.OK,
        message=f"RAG has {doc_count} documents loaded",
    ), False


async def _attempt_reload(
    client: httpx.AsyncClient, ai_assistant_url: str
) -> PreflightCheck:
    """Trigger context reload and verify it worked."""
    try:
        resp = await client.post(f"{ai_assistant_url}/orchestrator/context/reload")
    except Exception as exc:
        return PreflightCheck(
            name="rag_reload",
            status=CheckStatus.WARNING,
            message=f"Reload request failed: {exc}",
        )

    if resp.status_code != 200:
        return PreflightCheck(
            name="rag_reload",
            status=CheckStatus.WARNING,
            message=f"Reload returned HTTP {resp.status_code}",
        )

    try:
        data = resp.json()
    except Exception:
        data = {}

    success = data.get("success", False)
    status = data.get("status", {})
    adrs_loaded = status.get("adrs_loaded", False)

    if success and adrs_loaded:
        doc_count = status.get("rag_documents", 0)
        return PreflightCheck(
            name="rag_reload",
            status=CheckStatus.FIXED,
            message=f"Reloaded RAG context ({doc_count} documents)",
            fix_applied=f"triggered /orchestrator/context/reload ({doc_count} docs loaded)",
        )

    if success and not adrs_loaded:
        return PreflightCheck(
            name="rag_reload",
            status=CheckStatus.WARNING,
            message="Reload succeeded but ADRs still not loaded (adrs_loaded=False)",
        )

    return PreflightCheck(
        name="rag_reload",
        status=CheckStatus.WARNING,
        message=f"Reload response: {data}",
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def run_rag_preflight(force: bool = False) -> PreflightResult:
    """Run RAG pre-flight checks, returning a PreflightResult.

    Results are cached for `RAG_PREFLIGHT_CACHE_TTL` seconds (default 300).
    Pass force=True to bypass cache.
    """
    cfg = _get_config()

    if not force:
        cached = _get_cached(cfg["cache_ttl"])
        if cached is not None:
            logger.debug("RAG preflight cache hit")
            return cached

    checks: List[PreflightCheck] = []

    # Check 1: ADR source files on filesystem
    adr_check = _check_adr_source_files(cfg["qubinode_root"])
    checks.append(adr_check)

    # Check 2: Chunks file
    chunks_check = _check_chunks_file(cfg["rag_data_dir"])
    checks.append(chunks_check)

    needs_reload = chunks_check.status != CheckStatus.OK

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Check 3: Document count from health endpoint
        doc_check, health_needs_reload = await _check_rag_document_count(
            client, cfg["ai_assistant_url"]
        )
        checks.append(doc_check)

        needs_reload = needs_reload or health_needs_reload

        # Check 4: Auto-fix via reload (conditional)
        if needs_reload:
            reload_check = await _attempt_reload(client, cfg["ai_assistant_url"])
            checks.append(reload_check)

    result = PreflightResult(checks=checks, label="RAG Pre-flight")
    result.summary = result.format_report()
    _set_cached(result)
    return result
