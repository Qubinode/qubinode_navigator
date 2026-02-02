#!/usr/bin/env python3
"""
Unified Intent Parser MCP Server for Qubinode Navigator.

Exposes a single `qubinode(intent="...")` tool that accepts natural language
and routes to the appropriate backend function.

Port: 8890 (configurable via QUBINODE_INTENT_MCP_PORT)
Transport: SSE
"""

import os
import sys
import logging

try:
    from fastmcp import FastMCP
except ImportError:
    print(
        "Warning: fastmcp not installed. Intent MCP server will not be available.",
        file=sys.stderr,
    )
    print("Install with: pip install fastmcp pydantic httpx", file=sys.stderr)
    if __name__ != "__main__":
        raise SystemExit(0)
    else:
        raise

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("fastmcp-intent-parser")

# Configuration
MCP_ENABLED = os.getenv("QUBINODE_INTENT_MCP_ENABLED", "false").lower() == "true"
MCP_PORT = int(os.getenv("QUBINODE_INTENT_MCP_PORT", "8890"))
MCP_HOST = os.getenv("QUBINODE_INTENT_MCP_HOST", "0.0.0.0")

# Create FastMCP server
mcp = FastMCP(name="qubinode-intent-parser")

# Initialize the intent parser (registers all handlers)
from intent_parser import IntentParser  # noqa: E402

parser = IntentParser()

logger.info("=" * 60)
logger.info("Initializing FastMCP Intent Parser Server")
logger.info(f"Port: {MCP_PORT}")
logger.info(f"Enabled: {MCP_ENABLED}")
logger.info("=" * 60)


@mcp.tool()
async def qubinode(intent: str) -> str:
    """
    Execute any Qubinode operation using natural language.

    This is the unified entry point for all Qubinode Navigator operations.
    Describe what you want to do in plain English and the system will
    route your request to the appropriate backend function.

    Args:
        intent: Natural language description of what you want to do.

    Examples:
        - "list all vms"
        - "create a vm named test01 with 4GB RAM and 2 cpus"
        - "show dags"
        - "trigger the freeipa_deploy dag"
        - "system status"
        - "search rag for DNS configuration"
        - "diagnose vm not responding"
        - "blast radius for dag freeipa_deploy"

    Returns:
        Result of the operation, or helpful suggestions if the intent
        could not be understood.
    """
    logger.info(f"Tool called: qubinode(intent='{intent[:80]}...')")

    result = await parser.process(intent)

    if not result.success and result.suggestions:
        output = result.output + "\n\n**Suggestions:**\n"
        for suggestion in result.suggestions:
            output += f"- {suggestion}\n"
        return output

    return result.output


def main():
    """Main entry point."""
    if not MCP_ENABLED:
        logger.warning("=" * 60)
        logger.warning("Intent Parser MCP Server is DISABLED")
        logger.warning("To enable: export QUBINODE_INTENT_MCP_ENABLED=true")
        logger.warning("=" * 60)
        sys.exit(0)

    logger.info("=" * 60)
    logger.info("Starting FastMCP Intent Parser Server")
    logger.info(f"Host: {MCP_HOST}")
    logger.info(f"Port: {MCP_PORT}")
    logger.info("Tool: qubinode(intent='...')")
    logger.info("=" * 60)

    mcp.run(transport="sse", host=MCP_HOST, port=MCP_PORT)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
