"""
RAG operation handlers.

Delegates to existing functions from airflow/scripts/mcp_server_fastmcp.py.
"""

import logging
from typing import Dict

from ..router import register
from ..models import IntentCategory

logger = logging.getLogger("intent-parser.handlers.rag")

_backend_available = False
try:
    import sys
    import os

    _scripts_dir = os.path.join(os.path.dirname(__file__), "..", "..", "airflow", "scripts")
    _scripts_dir = os.path.normpath(_scripts_dir)
    if _scripts_dir not in sys.path:
        sys.path.insert(0, _scripts_dir)

    from mcp_server_fastmcp import (
        query_rag as _query_rag_tool,
        ingest_to_rag as _ingest_to_rag_tool,
        get_rag_stats as _get_rag_stats_tool,
    )

    def _unwrap(t):
        if callable(t):
            return t
        fn = getattr(t, "fn", None)
        if fn and callable(fn):
            return fn
        raise TypeError(f"Cannot unwrap {type(t)}")

    _query_rag = _unwrap(_query_rag_tool)
    _ingest_to_rag = _unwrap(_ingest_to_rag_tool)
    _get_rag_stats = _unwrap(_get_rag_stats_tool)

    _backend_available = True
    logger.info("RAG backend functions loaded")
except ImportError as e:
    logger.warning(f"RAG backend not available: {e}")


def _unavailable_msg(operation: str) -> str:
    return f"Error: RAG {operation} is not available. The Airflow MCP backend could not be loaded."


async def handle_rag_query(params: Dict) -> str:
    if not _backend_available:
        return _unavailable_msg("query")
    query = params.get("query")
    if not query:
        return "Error: Search query is required. Try: 'search rag for <query>'"
    return await _query_rag(
        query=query,
        doc_types=params.get("doc_types"),
        limit=params.get("limit", 5),
        threshold=params.get("threshold", 0.7),
    )


async def handle_rag_ingest(params: Dict) -> str:
    if not _backend_available:
        return _unavailable_msg("ingest")
    content = params.get("content")
    if not content:
        return "Error: Content is required for ingestion."
    return await _ingest_to_rag(
        content=content,
        doc_type=params.get("doc_type", "guide"),
        source=params.get("source"),
        metadata=params.get("metadata"),
    )


async def handle_rag_stats(params: Dict) -> str:
    if not _backend_available:
        return _unavailable_msg("stats")
    return await _get_rag_stats()


register(IntentCategory.RAG_QUERY, handle_rag_query)
register(IntentCategory.RAG_INGEST, handle_rag_ingest)
register(IntentCategory.RAG_STATS, handle_rag_stats)
