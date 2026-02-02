"""
Pydantic models for the Intent Parser Layer.

Defines intent categories, parsed intent structures, and result types
for deterministic natural language routing to backend functions.
"""

from enum import Enum
from typing import Dict, Any, List, Optional

from pydantic import BaseModel, Field


class IntentCategory(str, Enum):
    """Categories covering all existing MCP tool operations."""

    # VM operations
    VM_LIST = "vm.list"
    VM_INFO = "vm.info"
    VM_CREATE = "vm.create"
    VM_DELETE = "vm.delete"
    VM_PREFLIGHT = "vm.preflight"

    # DAG operations
    DAG_LIST = "dag.list"
    DAG_INFO = "dag.info"
    DAG_TRIGGER = "dag.trigger"

    # RAG operations
    RAG_QUERY = "rag.query"
    RAG_INGEST = "rag.ingest"
    RAG_STATS = "rag.stats"

    # System operations
    SYSTEM_STATUS = "system.status"
    SYSTEM_INFO = "system.info"

    # Troubleshooting
    TROUBLESHOOT_DIAGNOSE = "troubleshoot.diagnose"
    TROUBLESHOOT_HISTORY = "troubleshoot.history"
    TROUBLESHOOT_LOG = "troubleshoot.log"

    # Lineage
    LINEAGE_DAG = "lineage.dag"
    LINEAGE_BLAST_RADIUS = "lineage.blast_radius"

    # Meta
    HELP = "help"
    UNKNOWN = "unknown"


# Categories that require write access
WRITE_CATEGORIES = frozenset(
    {
        IntentCategory.VM_CREATE,
        IntentCategory.VM_DELETE,
        IntentCategory.DAG_TRIGGER,
        IntentCategory.RAG_INGEST,
        IntentCategory.TROUBLESHOOT_LOG,
    }
)


class ParsedIntent(BaseModel):
    """Result of classifying a natural language input."""

    category: IntentCategory
    confidence: float = Field(ge=0.0, le=1.0)
    raw_input: str
    entities: Dict[str, Any] = Field(default_factory=dict)
    parameters: Dict[str, Any] = Field(default_factory=dict)


class IntentResult(BaseModel):
    """Result from executing a routed intent."""

    success: bool
    output: str
    error: Optional[str] = None
    suggestions: List[str] = Field(default_factory=list)
