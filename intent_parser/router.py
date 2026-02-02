"""
Intent router that maps IntentCategory to handler functions and dispatches.
"""

import logging
import os
from typing import Callable, Awaitable, Dict, Optional

from .models import IntentCategory, IntentResult, ParsedIntent, WRITE_CATEGORIES
from .classifier import classify
from .entity_extractor import extract

logger = logging.getLogger("intent-parser")

# Type for handler functions
HandlerFunc = Callable[[Dict], Awaitable[str]]

# Registry of category -> handler
_handlers: Dict[IntentCategory, HandlerFunc] = {}


def register(category: IntentCategory, handler: HandlerFunc) -> None:
    """Register a handler function for an intent category."""
    _handlers[category] = handler
    logger.debug(f"Registered handler for {category.value}")


def get_handler(category: IntentCategory) -> Optional[HandlerFunc]:
    """Get the registered handler for a category."""
    return _handlers.get(category)


def _is_read_only() -> bool:
    """Check if write operations are blocked."""
    return os.getenv("AIRFLOW_MCP_TOOLS_READ_ONLY", "false").lower() == "true"


async def route(text: str) -> IntentResult:
    """
    Classify input text, extract parameters, and route to the appropriate handler.

    This is the main entry point for processing natural language intents.
    """
    # Step 1: Classify
    intent = classify(text)

    # Step 2: Extract entities/parameters
    params = extract(text, intent.category)
    intent.entities = params
    intent.parameters = params

    # Step 3: Handle unknown
    if intent.category == IntentCategory.UNKNOWN:
        return IntentResult(
            success=False,
            output="I couldn't understand that request.",
            suggestions=[
                "Try: 'list vms', 'show dags', 'create a vm named test01'",
                "Try: 'system status', 'search rag for DNS configuration'",
                "Try: 'help' for a full list of capabilities",
            ],
        )

    # Step 4: Handle help
    if intent.category == IntentCategory.HELP:
        return IntentResult(
            success=True,
            output=_help_text(),
        )

    # Step 5: Check read-only mode for write operations
    if intent.category in WRITE_CATEGORIES and _is_read_only():
        return IntentResult(
            success=False,
            output=f"Cannot perform '{intent.category.value}' in read-only mode.",
            error="Read-only mode is enabled (AIRFLOW_MCP_TOOLS_READ_ONLY=true)",
            suggestions=["Set AIRFLOW_MCP_TOOLS_READ_ONLY=false to enable write operations"],
        )

    # Step 6: Find handler
    handler = get_handler(intent.category)
    if handler is None:
        return IntentResult(
            success=False,
            output=f"No handler registered for intent '{intent.category.value}'.",
            error="Handler not found",
            suggestions=["This operation may not be available in the current environment."],
        )

    # Step 7: Execute handler
    try:
        output = await handler(params)
        return IntentResult(
            success=True,
            output=output,
        )
    except Exception as e:
        logger.error(f"Handler error for {intent.category.value}: {e}", exc_info=True)
        return IntentResult(
            success=False,
            output=f"Error executing '{intent.category.value}': {str(e)}",
            error=str(e),
            suggestions=[
                "Check that required services are running.",
                "Try 'system status' to verify system health.",
            ],
        )


def _help_text() -> str:
    """Generate help text listing all available operations."""
    return """# Qubinode Intent Parser - Available Operations

## VM Operations
- **list vms** - Show all virtual machines
- **vm info <name>** - Get details about a specific VM
- **create vm named <name>** - Create a new VM (supports: image, memory, cpus, disk_size)
- **delete vm <name>** - Delete a virtual machine
- **preflight check for vm <name>** - Run pre-creation checks

## DAG / Workflow Operations
- **list dags** - Show all available Airflow DAGs
- **dag info <dag_id>** - Get details about a specific DAG
- **trigger dag <dag_id>** - Execute a DAG workflow

## RAG / Knowledge Base
- **search rag for <query>** - Search the knowledge base
- **ingest documents** - Add content to the knowledge base
- **rag stats** - Get knowledge base statistics

## System
- **system status** - Check system health
- **system info** - Get architecture and capability overview

## Troubleshooting
- **diagnose <symptom>** - Get structured diagnostic guidance
- **troubleshooting history** - View past solutions
- **log solution** - Record a troubleshooting outcome

## Lineage
- **lineage for dag <dag_id>** - View DAG dependencies
- **blast radius for dag <dag_id>** - Analyze failure impact

## Tips
- Use natural language: "show me all VMs", "create a vm named test01 with 4GB RAM"
- Explicit params work too: "create vm name=test01 memory=4096 cpus=2"
"""
