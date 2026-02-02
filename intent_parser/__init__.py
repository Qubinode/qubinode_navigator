"""
Intent Parser Layer for Qubinode Navigator.

Provides a single-tool MCP interface that accepts natural language and
deterministically routes to existing backend functions.

Usage:
    from intent_parser import IntentParser

    parser = IntentParser()
    result = await parser.process("list all vms")
    print(result.output)
"""

from .models import IntentCategory, ParsedIntent, IntentResult
from .classifier import classify
from .entity_extractor import extract
from .router import route


class IntentParser:
    """High-level interface for intent parsing and routing."""

    def __init__(self) -> None:
        """Initialize the parser and register all handlers."""
        from .handlers import register_all_handlers
        register_all_handlers()

    async def process(self, text: str) -> IntentResult:
        """Process natural language input and return the result."""
        return await route(text)

    def classify(self, text: str) -> ParsedIntent:
        """Classify text without executing (useful for testing)."""
        intent = classify(text)
        params = extract(text, intent.category)
        intent.entities = params
        intent.parameters = params
        return intent


__all__ = [
    "IntentParser",
    "IntentCategory",
    "ParsedIntent",
    "IntentResult",
    "classify",
    "extract",
    "route",
]
